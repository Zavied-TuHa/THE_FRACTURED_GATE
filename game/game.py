"""Main Game controller managing the 60 FPS loop, nearest-neighbor scaling, and states."""

from __future__ import annotations

import pygame

from config.controls import (
    KEY_DASH,
    KEY_INTERACT,
    KEY_MOVE_DOWN,
    KEY_MOVE_LEFT,
    KEY_MOVE_RIGHT,
    KEY_MOVE_UP,
    KEY_PAUSE,
    KEY_SKILL_1,
    KEY_SKILL_2,
    MOUSE_BASIC_ATTACK,
)
from config.settings import (
    COLOR_BG_VOID,
    COLOR_PORTAL,
    GAME_TITLE,
    INTERNAL_RESOLUTION,
    TARGET_FPS,
    WINDOW_RESOLUTION,
)
from entities.boss import Boss
from game.camera import AtmosphericLighting, Camera
from game.event_manager import EventManager
from game.state_manager import GameState, StateManager
from systems.progression import ProgressionManager
from systems.run_manager import RunManager
from systems.save_system import SaveSystem
from ui.character_selection import CharacterSelectionScreen
from ui.hud import GameplayHUD
from ui.main_menu import MainMenuScreen
from ui.menus import EndRunScreen, PauseMenuOverlay, TreasureRoomScreen


class FracturedGateGame:
    """Top-level game class encapsulating display scaling, state updates, and rendering."""

    def __init__(self, headless: bool = False) -> None:
        pygame.init()
        pygame.font.init()

        self.headless: bool = headless
        flags = pygame.RESIZABLE
        if headless:
            self.window_surface: pygame.Surface = pygame.Surface(WINDOW_RESOLUTION)
        else:
            pygame.display.set_caption(GAME_TITLE)
            self.window_surface = pygame.display.set_mode(WINDOW_RESOLUTION, flags)

        # Internal 640x360 pixel-art canvas scaled via nearest-neighbor to window
        self.internal_surface: pygame.Surface = pygame.Surface(INTERNAL_RESOLUTION)
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.running: bool = True

        # Crisp pixel-friendly system fonts
        self.title_font: pygame.font.Font = pygame.font.SysFont("consolas", 18, bold=True)
        self.body_font: pygame.font.Font = pygame.font.SysFont("consolas", 13, bold=True)
        self.small_font: pygame.font.Font = pygame.font.SysFont("consolas", 11)

        # Core systems
        self.event_manager: EventManager = EventManager()
        self.save_system: SaveSystem = SaveSystem()
        self.progression: ProgressionManager = ProgressionManager(self.save_system)
        self.run_manager: RunManager = RunManager(self.progression)
        self.state_manager: StateManager = StateManager(GameState.MAIN_MENU)
        self.camera: Camera = Camera()
        self.lighting: AtmosphericLighting = AtmosphericLighting()

        # UI Screens
        self.main_menu: MainMenuScreen = MainMenuScreen()
        self.char_select: CharacterSelectionScreen = CharacterSelectionScreen()
        self.hud: GameplayHUD = GameplayHUD()
        self.pause_menu: PauseMenuOverlay = PauseMenuOverlay()
        self.treasure_screen: TreasureRoomScreen = TreasureRoomScreen()
        self.victory_screen: EndRunScreen = EndRunScreen(is_victory=True)
        self.game_over_screen: EndRunScreen = EndRunScreen(is_victory=False)

    def run(self, max_frames: int | None = None) -> None:
        """Execute the main 60 FPS game loop."""
        frames = 0
        while self.running:
            dt = min(0.05, self.clock.tick(TARGET_FPS) / 1000.0)
            self.process_events()
            self.update(dt)
            self.render()

            frames += 1
            if max_frames is not None and frames >= max_frames:
                self.running = False

        pygame.quit()

    def process_events(self) -> None:
        """Poll Pygame events and route them to the active state."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.VIDEORESIZE and not self.headless:
                new_w = max(640, event.w)
                new_h = max(360, event.h)
                self.window_surface = pygame.display.set_mode(
                    (new_w, new_h), pygame.RESIZABLE
                )

            if event.type == pygame.KEYDOWN:
                self._handle_keydown(event.key)

            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == MOUSE_BASIC_ATTACK
                and self.state_manager.current_state == GameState.GAMEPLAY
            ):
                self._try_player_basic_attack()

    def _handle_keydown(self, key: int) -> None:
        """Route keydown events according to current GameState."""
        state = self.state_manager.current_state

        if state == GameState.MAIN_MENU:
            action = self.main_menu.handle_keydown(key)
            if action == "character_selection":
                self.state_manager.change_state(GameState.CHARACTER_SELECTION)
            elif action == "quit":
                self.running = False

        elif state == GameState.CHARACTER_SELECTION:
            action = self.char_select.handle_keydown(key, self.progression)
            if action == "main_menu":
                self.state_manager.change_state(GameState.MAIN_MENU)
            elif action and action.startswith("start_run:"):
                char_id = action.split(":", 1)[1]
                self.run_manager.start_new_run(character_id=char_id)
                if self.run_manager.player is not None:
                    self.camera.snap_to(
                        self.run_manager.player.x,
                        self.run_manager.player.y,
                    )
                self.state_manager.change_state(GameState.GAMEPLAY)

        elif state == GameState.GAMEPLAY:
            if key == KEY_PAUSE:
                self.state_manager.change_state(GameState.PAUSED)
                return
            self._handle_gameplay_keydown(key)

        elif state == GameState.PAUSED:
            action = self.pause_menu.handle_keydown(key)
            if action == "resume":
                self.state_manager.change_state(GameState.GAMEPLAY)
            elif action == "character_selection":
                self.state_manager.change_state(GameState.CHARACTER_SELECTION)
            elif action == "main_menu":
                self.state_manager.change_state(GameState.MAIN_MENU)

        elif state == GameState.TREASURE_ROOM:
            action = self.treasure_screen.handle_keydown(key, self.run_manager)
            if action == "victory":
                self.state_manager.change_state(GameState.VICTORY)

        elif state == GameState.VICTORY:
            action = self.victory_screen.handle_keydown(key)
            if action == "character_selection":
                self.state_manager.change_state(GameState.CHARACTER_SELECTION)
            elif action == "main_menu":
                self.state_manager.change_state(GameState.MAIN_MENU)

        elif state == GameState.GAME_OVER:
            action = self.game_over_screen.handle_keydown(key)
            if action == "character_selection":
                self.state_manager.change_state(GameState.CHARACTER_SELECTION)
            elif action == "main_menu":
                self.state_manager.change_state(GameState.MAIN_MENU)

    def _handle_gameplay_keydown(self, key: int) -> None:
        """Process active combat skills, dodge-dash, and shrine/portal interactions."""
        player = self.run_manager.player
        dungeon = self.run_manager.dungeon
        shrine_sys = self.run_manager.shrine_system
        if player is None or dungeon is None or shrine_sys is None:
            return

        if key == KEY_DASH:
            move_dx, move_dy = self._read_movement_axes()
            player.try_dash(move_dx, move_dy)
        elif key == KEY_SKILL_1:
            if player.trigger_skill(1):
                self.run_manager.combat_system.spawn_player_skill(
                    player, 1, player.facing_x, player.facing_y
                )
            elif not player.skill_1_unlocked:
                self.run_manager.show_banner(
                    "Skill 1 [Q] is Locked! Unlock it with Gold in Character Selection."
                )
        elif key == KEY_SKILL_2:
            if player.trigger_skill(2):
                self.run_manager.combat_system.spawn_player_skill(
                    player, 2, player.facing_x, player.facing_y
                )
            elif not player.skill_2_unlocked:
                self.run_manager.show_banner(
                    "Skill 2 [E] is Locked! Unlock it with Gold in Character Selection."
                )
        elif key == KEY_INTERACT:
            # 1. Check Stage Exit Portal interaction
            if self.run_manager.portal is not None and self.run_manager.portal.is_player_in_range(
                player.x, player.y
            ):
                next_state = self.run_manager.advance_stage_or_finish()
                if next_state == "treasure_room":
                    self.state_manager.change_state(GameState.TREASURE_ROOM)
                else:
                    self.camera.snap_to(player.x, player.y)
                return

            # 2. Check Shrine activation
            activated, msg, gold, crystals = shrine_sys.try_activate_nearby_shrine(
                player.x,
                player.y,
                self.run_manager.enemies,
                dungeon.tilemap,
            )
            if msg:
                self.run_manager.show_banner(msg)
            if activated:
                self.run_manager.award_currency(gold=gold, crystals=crystals)

    def _try_player_basic_attack(self) -> None:
        """Fire basic attack toward current mouse cursor if off cooldown."""
        player = self.run_manager.player
        if player is None:
            return
        mx, my = pygame.mouse.get_pos()
        wx, wy = self.camera.window_to_world((mx, my), self.window_surface.get_size())
        player.update_aim(wx, wy)
        if player.trigger_basic_attack():
            self.run_manager.combat_system.spawn_player_basic_attack(
                player, player.facing_x, player.facing_y
            )

    def _read_movement_axes(self) -> tuple[float, float]:
        """Read held WASD / Arrow keys and return raw (dx, dy) movement input."""
        keys = pygame.key.get_pressed()
        dx = 0.0
        dy = 0.0
        if any(keys[k] for k in KEY_MOVE_LEFT):
            dx -= 1.0
        if any(keys[k] for k in KEY_MOVE_RIGHT):
            dx += 1.0
        if any(keys[k] for k in KEY_MOVE_UP):
            dy -= 1.0
        if any(keys[k] for k in KEY_MOVE_DOWN):
            dy += 1.0
        return (dx, dy)

    def update(self, dt: float) -> None:
        """Update active gameplay entities, AI, combat hits, and camera."""
        if self.state_manager.current_state != GameState.GAMEPLAY:
            return

        player = self.run_manager.player
        dungeon = self.run_manager.dungeon
        if player is None or dungeon is None:
            return

        if self.run_manager.status_banner_timer > 0.0:
            self.run_manager.status_banner_timer = max(
                0.0, self.run_manager.status_banner_timer - dt
            )

        # Update player aim, continuous LMB attack, and movement
        mx, my = pygame.mouse.get_pos()
        wx, wy = self.camera.window_to_world((mx, my), self.window_surface.get_size())
        player.update_aim(wx, wy)

        if pygame.mouse.get_pressed()[0] and player.trigger_basic_attack():
            self.run_manager.combat_system.spawn_player_basic_attack(
                player, player.facing_x, player.facing_y
            )

        move_dx, move_dy = self._read_movement_axes()
        player.update(dt, move_dx, move_dy, dungeon.tilemap)

        # Update enemies
        for enemy in self.run_manager.enemies:
            if enemy.alive:
                enemy.update(
                    dt,
                    player,
                    dungeon.tilemap,
                    self.run_manager.combat_system,
                    self.run_manager._stage_rng,
                )

        # Update combat system and process enemy kills
        killed = self.run_manager.combat_system.update(
            dt, player, self.run_manager.enemies, dungeon.tilemap
        )
        for dead_enemy in killed:
            self.run_manager.enemies_slain += 1
            if isinstance(dead_enemy, Boss):
                self.run_manager.handle_boss_defeated()
            else:
                self.run_manager.award_currency(
                    gold=dead_enemy.gold_drop,
                    crystals=dead_enemy.crystal_drop,
                )

        # Check player death (wait for highest-priority DEATH animation to finish)
        if not player.alive:
            if player.anim_controller.finished:
                self.state_manager.change_state(GameState.GAME_OVER)
                return

        self.camera.update(player.x, player.y, dt)

    def render(self) -> None:
        """Render the current state to the 640x360 internal surface, then nearest-neighbor scale."""
        state = self.state_manager.current_state

        if state == GameState.MAIN_MENU:
            self.main_menu.render(
                self.internal_surface,
                self.title_font,
                self.body_font,
                self.small_font,
                self.progression,
            )
        elif state == GameState.CHARACTER_SELECTION:
            self.char_select.render(
                self.internal_surface,
                self.title_font,
                self.body_font,
                self.small_font,
                self.progression,
            )
        elif state in (GameState.GAMEPLAY, GameState.PAUSED):
            self._render_gameplay_world()
            self.hud.render(
                self.internal_surface,
                self.run_manager,
                self.body_font,
                self.small_font,
            )
            if state == GameState.PAUSED:
                self.pause_menu.render(
                    self.internal_surface,
                    self.title_font,
                    self.body_font,
                )
        elif state == GameState.TREASURE_ROOM:
            self.treasure_screen.render(
                self.internal_surface,
                self.run_manager,
                self.title_font,
                self.body_font,
                self.small_font,
            )
        elif state == GameState.VICTORY:
            self.victory_screen.render(
                self.internal_surface,
                self.run_manager,
                self.title_font,
                self.body_font,
                self.small_font,
            )
        elif state == GameState.GAME_OVER:
            self.game_over_screen.render(
                self.internal_surface,
                self.run_manager,
                self.title_font,
                self.body_font,
                self.small_font,
            )

        # Nearest-neighbor scale internal 640x360 buffer to actual window size
        pygame.transform.scale(
            self.internal_surface,
            self.window_surface.get_size(),
            self.window_surface,
        )
        if not self.headless:
            pygame.display.flip()

    def _render_gameplay_world(self) -> None:
        """Render layered tilemap, Y-sorted entities by foot_y, foreground tiles, and lighting."""
        self.internal_surface.fill(COLOR_BG_VOID)
        dungeon = self.run_manager.dungeon
        player = self.run_manager.player
        shrine_sys = self.run_manager.shrine_system
        if dungeon is None or player is None or shrine_sys is None:
            return

        cam_offset = self.camera.offset
        # 1. Ground, Decoration, and Wall Base layers
        dungeon.tilemap.render(self.internal_surface, cam_offset)

        if self.run_manager.portal is not None:
            wx, wy = self.run_manager.portal.world_pos
            sx = int(round(wx - cam_offset[0]))
            sy = int(round(wy - cam_offset[1]))
            pygame.draw.circle(self.internal_surface, COLOR_PORTAL, (sx, sy), 10)
            pygame.draw.circle(self.internal_surface, (235, 210, 255), (sx, sy), 6, 2)

        # 2. Y-Sorted Entities based on foot_y (Shrines, Enemies/Boss, Player)
        renderables: list[tuple[float, object]] = []
        for shrine in shrine_sys.shrines:
            renderables.append((shrine.foot_y, shrine))
        for enemy in self.run_manager.enemies:
            if enemy.alive:
                renderables.append((enemy.foot_y, enemy))
        renderables.append((player.foot_y, player))

        renderables.sort(key=lambda item: item[0])

        for _, obj in renderables:
            if obj is player:
                player.render(self.internal_surface, cam_offset)
            elif hasattr(obj, "shrine_id"):
                guarded = shrine_sys.is_shrine_guarded(obj, self.run_manager.enemies)  # type: ignore[arg-type]
                obj.render(self.internal_surface, cam_offset, guarded=guarded)  # type: ignore[attr-defined]
            else:
                obj.render(self.internal_surface, cam_offset)  # type: ignore[attr-defined]

        # 3. Foreground Tile Layer (upper wall crowns overlapping entities behind southern walls)
        dungeon.tilemap.render_foreground(self.internal_surface, cam_offset)

        # 4. Combat slashes, projectiles, floating damage numbers, and lighting vignette
        self.run_manager.combat_system.render(
            self.internal_surface, cam_offset, self.small_font
        )
        self.lighting.render(self.internal_surface)
