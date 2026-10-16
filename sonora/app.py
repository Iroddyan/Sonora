from __future__ import annotations

import sys
import json
import random
import unicodedata
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Adw, Gio, GLib, Gtk, Gdk, GdkPixbuf
from mutagen import File as MutagenFile

from sonora.library import LibraryService
from sonora.models import Track
from sonora.mpris import MprisService
from sonora.playback import PlaybackService


APP_ID = "io.github.Iroddyan.Sonora"


class SonoraApplication(Adw.Application):
    def __init__(self, smoke_test=False):
        flags = Gio.ApplicationFlags.NON_UNIQUE if smoke_test else Gio.ApplicationFlags.DEFAULT_FLAGS
        super().__init__(application_id=APP_ID, flags=flags)
        self.smoke_test = smoke_test
        self.connect("activate", self._activate)

    def _activate(self, app):
        if getattr(self, "window", None):
            self.window.present()
            return
        self.window = SonoraWindow(self, self.smoke_test)
        self.window.present()


class SonoraWindow(Adw.ApplicationWindow):
    def __init__(self, app, smoke_test=False):
        super().__init__(application=app, title="Sonora", default_width=1240, default_height=820)
        self.set_size_request(720, 540)
        self._active_page = "listen"
        self._updating_seek = False
        self._updating_volume = False
        self._accent_provider = None
        self._detail_history = []
        self._grid_sort = {"albums": "Name", "artists": "Name"}
        self._grid_letter = {"albums": "", "artists": ""}
        self._grid_render_generation = {"albums": 0, "artists": 0}
        self._collection_cache = {"albums": [], "artists": []}
        self._artist_track_map = {}
        self._album_track_map = {}
        self._detail_page_name = None
        self._detail_page_names = []
        self._detail_scrolls = {}
        self._detail_indicator_starts = {}
        self._detail_indicators = []
        self._last_persist = 0.0
        self._show_remaining = False
        self._pending_playback_errors = []
        self._nav_rows = {}
        self._playlist_nav_rows = {}
        self._active_playlist_id = None
        self._song_refresh_generation = 0
        self._artwork_pixbufs = {}
        self.library = LibraryService(self._refresh, self._scan_progress_changed)
        self.playback = PlaybackService(
            self._sync_player,
            on_session_started=self.library.database.start_playback,
            on_listened=self._record_listened_time,
            on_session_ended=self._finish_playback_session,
            on_error=self._playback_error,
        )
        self._restore_playback_state()
        self.mpris = None
        try:
            self.mpris = MprisService(self.playback, self.present, app.quit, self._open_uri)
        except Exception as error:
            print(f"Sonora: MPRIS is unavailable: {error}", file=sys.stderr)

        self._build_ui()
        self._refresh()
        self._sync_player()
        self._position_timer = GLib.timeout_add(500, self._tick)
        self.connect("close-request", self._close)
        if smoke_test:
            GLib.timeout_add(900, self._smoke_quit)

    def _build_ui(self):
        self.split = Adw.NavigationSplitView()
        self.split.set_min_sidebar_width(205)
        self.split.set_max_sidebar_width(260)
        self.split.set_sidebar_width_fraction(0.22)
        breakpoint = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 840sp"))
        breakpoint.add_setter(self.split, "collapsed", True)
        self.add_breakpoint(breakpoint)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar.set_margin_top(8)
        sidebar.set_margin_bottom(8)
        sidebar.add_css_class("navigation-sidebar")
        brand = Adw.HeaderBar()
        brand.set_title_widget(Gtk.Label(label="Sonora", css_classes=["title-2"]))
        sidebar.append(brand)

        self.sidebar_add_button = Gtk.Button(label="Add music folder")
        self.sidebar_add_button.set_icon_name("folder-new-symbolic")
        self.sidebar_add_button.add_css_class("suggested-action")
        self.sidebar_add_button.set_halign(Gtk.Align.FILL)
        self.sidebar_add_button.set_margin_start(16)
        self.sidebar_add_button.set_margin_end(16)
        self.sidebar_add_button.set_margin_top(12)
        self.sidebar_add_button.set_margin_bottom(4)
        self.sidebar_add_button.connect("clicked", self._choose_folder)
        sidebar.append(self.sidebar_add_button)

        self.nav_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.nav_list.add_css_class("navigation-sidebar")
        self.nav_list.set_margin_start(8)
        self.nav_list.set_margin_end(8)
        self.nav_list.set_margin_top(8)
        self.nav_list.set_vexpand(False)
        self.nav_list.connect("row-selected", self._on_nav_selected)
        self.nav_scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER,
                                             vscrollbar_policy=Gtk.PolicyType.AUTOMATIC)
        self.nav_scroll.set_child(self.nav_list)
        sidebar.append(self.nav_scroll)
        self._nav_rows = {}
        for key, title, icon in (
            ("listen", "Listen Now", "audio-x-generic-symbolic"),
            ("songs", "Songs", "view-list-symbolic"),
            ("albums", "Albums", "media-optical-symbolic"),
            ("artists", "Artists", "avatar-default-symbolic"),
            ("favorites", "Favorites", "starred-symbolic"),
        ):
            row = Adw.ActionRow(title=title)
            row.set_activatable(True)
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
            row.sonora_page = key
            self.nav_list.append(row)
            self._nav_rows[key] = row
        self.playlist_nav_header = Gtk.ListBoxRow(child=Gtk.Label(label="Your Playlists", xalign=0))
        self.playlist_nav_header.set_selectable(False)
        self.playlist_nav_header.set_activatable(False)
        self.playlist_nav_header.add_css_class("dim-label")
        self.playlist_nav_header.set_margin_start(12)
        self.playlist_nav_header.set_margin_top(12)
        self.nav_list.append(self.playlist_nav_header)
        self._refresh_playlist_nav()
        self.new_playlist_button = Gtk.Button(label="New playlist")
        self.new_playlist_button.set_icon_name("list-add-symbolic")
        self.new_playlist_button.set_halign(Gtk.Align.FILL)
        self.new_playlist_button.set_margin_start(16)
        self.new_playlist_button.set_margin_end(16)
        self.new_playlist_button.set_margin_bottom(8)
        self.new_playlist_button.connect("clicked", self._create_playlist_dialog)
        sidebar.append(self.new_playlist_button)
        self.import_playlist_button = Gtk.Button(label="Import M3U playlist")
        self.import_playlist_button.set_icon_name("document-open-symbolic")
        self.import_playlist_button.set_halign(Gtk.Align.FILL)
        self.import_playlist_button.set_margin_start(16)
        self.import_playlist_button.set_margin_end(16)
        self.import_playlist_button.set_margin_bottom(8)
        self.import_playlist_button.connect("clicked", self._import_m3u_dialog)
        sidebar.append(self.import_playlist_button)
        sidebar.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self.settings_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.settings_list.set_margin_start(8)
        self.settings_list.set_margin_end(8)
        self.settings_list.connect("row-selected", self._on_nav_selected)
        self.settings_row = Adw.ActionRow(title="Settings")
        self.settings_row.set_activatable(True)
        self.settings_row.add_prefix(Gtk.Image.new_from_icon_name("preferences-system-symbolic"))
        self.settings_row.sonora_page = "settings"
        self.settings_list.append(self.settings_row)
        sidebar.append(self.settings_list)

        self.sidebar_page = Adw.NavigationPage(child=sidebar, title="Library")
        self.content_toolbar = Adw.ToolbarView()
        self.header = Adw.HeaderBar()
        self.header_title = Gtk.Label(label="Listen Now", css_classes=["title-2"])
        self.header.set_title_widget(self.header_title)
        self.back_button = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        self.back_button.set_tooltip_text("Back")
        self.back_button.set_visible(False)
        self.back_button.connect("clicked", lambda *_: self._go_back())
        self.header.pack_start(self.back_button)
        self.split.connect("notify::collapsed", self._update_back_button)
        self.split.connect("notify::show-content", self._update_back_button)
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search your music")
        self.search_entry.set_width_chars(30)
        self.search_entry.set_size_request(280, -1)
        self.search_entry.add_css_class("sonora-search")
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("activate", self._on_search_activate)
        self.header.pack_end(self.search_entry)
        breakpoint.add_setter(self.search_entry, "width-request", 192)
        self.content_toolbar.add_top_bar(self.header)
        self.search_results = Gtk.Popover()
        self.search_results.set_parent(self.search_entry)
        self.search_results.set_position(Gtk.PositionType.BOTTOM)
        self.search_results.set_autohide(True)
        self.search_results_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.search_results_content.set_margin_top(10)
        self.search_results_content.set_margin_bottom(10)
        self.search_results_content.set_margin_start(10)
        self.search_results_content.set_margin_end(10)
        self.search_results_content.set_size_request(360, -1)
        self.search_results.set_child(self.search_results_content)
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key_pressed)
        self.add_controller(keys)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=160)
        self.stack.set_vexpand(True)
        self._build_listen_page()
        self._build_songs_page()
        self._build_albums_page()
        self._build_artists_page()
        self._build_settings_page()
        self._build_favorites_page()
        self.content_toolbar.set_content(self.stack)
        self._build_player()
        compact_player = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 760sp"))
        compact_player.add_setter(self.position_label, "visible", False)
        compact_player.add_setter(self.duration_label, "visible", False)
        compact_player.add_setter(self.player_details, "width-request", 132)
        compact_player.add_setter(self.volume_scale, "width-request", 64)
        self.add_breakpoint(compact_player)
        self.content_toolbar.add_bottom_bar(self.player_bar)

        self.content_page = Adw.NavigationPage(child=self.content_toolbar, title="Sonora")
        self.split.set_sidebar(self.sidebar_page)
        self.split.set_content(self.content_page)
        self.toast_overlay = Adw.ToastOverlay(child=self.split)
        self.set_content(self.toast_overlay)
        for message in self._pending_playback_errors:
            self.toast_overlay.add_toast(Adw.Toast.new(message))
        self._pending_playback_errors.clear()
        self._install_artwork_styles()
        self.nav_list.select_row(self.nav_list.get_row_at_index(0))

    def _install_artwork_styles(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(b"""
            image.sonora-artwork-large { border-radius: 18px; }
            image.sonora-artwork-small { border-radius: 9px; }
        """)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self._artwork_style_provider = provider

    def _build_listen_page(self):
        self.listen_page = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                              vscrollbar_policy=Gtk.PolicyType.AUTOMATIC)
        self.listen_page.set_vexpand(True)
        self.listen_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=30)
        self.listen_content.set_margin_start(28)
        self.listen_content.set_margin_end(28)
        self.listen_content.set_margin_top(28)
        self.listen_content.set_margin_bottom(32)
        self.listen_page.set_child(self.listen_content)

        hero = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        hero_labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        hero_labels.set_hexpand(True)
        hero_labels.set_valign(Gtk.Align.CENTER)
        self.home_description = Gtk.Label(label="Your music, in one place.", xalign=0)
        self.home_description.add_css_class("dim-label")
        self.home_library_status = Gtk.Label(xalign=0)
        self.home_library_status.add_css_class("dim-label")
        hero_labels.append(self.home_description)
        hero_labels.append(self.home_library_status)
        hero.append(hero_labels)
        self.home_play_all = Gtk.Button(label="Play all")
        self.home_play_all.add_css_class("suggested-action")
        self.home_play_all.set_valign(Gtk.Align.CENTER)
        self.home_play_all.connect("clicked", self._play_all)
        hero.append(self.home_play_all)
        self.listen_content.append(hero)

        self.home_empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.home_empty.set_halign(Gtk.Align.CENTER)
        self.home_empty.set_valign(Gtk.Align.CENTER)
        self.home_empty.set_vexpand(True)
        empty_status = Adw.StatusPage(icon_name="folder-music-symbolic", title="Start with your music folder")
        empty_status.set_description("Sonora will build a library from your local music. Your files stay where they are.")
        self.home_empty.append(empty_status)
        choose_folder = Gtk.Button(label="Choose a music folder")
        choose_folder.add_css_class("suggested-action")
        choose_folder.set_halign(Gtk.Align.CENTER)
        choose_folder.connect("clicked", self._choose_folder)
        self.home_empty.append(choose_folder)
        self.listen_content.append(self.home_empty)

        self.home_shelves = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=30)
        self.home_jump = self._home_section("Jump back in", "songs")
        self.home_played = self._home_section("Recently played", "songs")
        self.home_most_played = self._home_section("Most played", "songs")
        self.home_recent = self._home_section("Recently added", "songs")
        self.home_rediscover = self._home_section("Rediscover", "songs")
        self.home_random_albums = self._home_section("Random albums", "albums")
        for section in (self.home_jump, self.home_played, self.home_most_played,
                        self.home_recent, self.home_rediscover, self.home_random_albums):
            self.home_shelves.append(section["widget"])
        self.listen_content.append(self.home_shelves)
        self.stack.add_named(self.listen_page, "listen")

    def _home_section(self, title, destination, vertical=False):
        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        heading = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        label = Gtk.Label(label=title, xalign=0, css_classes=["title-2"])
        label.set_hexpand(True)
        heading.append(label)
        view_all = Gtk.Button(label="View all")
        view_all.add_css_class("flat")
        view_all.connect("clicked", lambda *_: self._navigate_to(destination))
        heading.append(view_all)
        section.append(heading)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL,
                          spacing=8 if vertical else 14)
        if vertical:
            section.append(content)
        else:
            scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
                                          vscrollbar_policy=Gtk.PolicyType.NEVER)
            scroller.set_min_content_height(226)
            scroller.set_child(content)
            section.append(scroller)
        return {"widget": section, "content": content}

    def _build_songs_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(14)
        self.scan_status = Gtk.Label(xalign=0)
        self.scan_status.add_css_class("dim-label")
        self.scan_status.set_margin_bottom(8)
        box.append(self.scan_status)
        self.song_columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.song_columns.set_margin_start(62)
        self.song_columns.set_margin_end(72)
        self.song_columns.set_margin_bottom(6)
        self.song_columns.add_css_class("dim-label")
        title_heading = Gtk.Label(label="Title", xalign=0)
        title_heading.set_hexpand(True)
        self.song_columns.append(title_heading)
        for heading in ("Artist", "Album"):
            label = Gtk.Label(label=heading, xalign=0)
            label.set_size_request(140, -1)
            self.song_columns.append(label)
        time_heading = Gtk.Label(label="Time", xalign=1)
        time_heading.set_size_request(48, -1)
        self.song_columns.append(time_heading)
        box.append(self.song_columns)
        scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.songs_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.songs_list.add_css_class("boxed-list")
        self.songs_list.set_placeholder(Gtk.Label(label="No songs match your search."))
        self.songs_list.connect("row-activated", self._activate_track_row)
        scroll.set_child(self.songs_list)
        self.songs_scroll = scroll
        box.append(scroll)
        self.stack.add_named(box, "songs")

    def _build_albums_page(self):
        box = self._page_list()
        self.albums_controls, self.albums_sort = self._build_grid_controls("albums")
        box.append(self.albums_controls)
        self.albums_empty = Adw.StatusPage(icon_name="media-optical-symbolic", title="No albums yet",
                                           description="Album groups appear after Sonora indexes music with album tags.")
        self.albums_empty.set_vexpand(True)
        box.append(self.albums_empty)
        self.albums_scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.albums_grid = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, min_children_per_line=2,
                                       max_children_per_line=7, row_spacing=18, column_spacing=14)
        self.albums_grid.set_homogeneous(True)
        self.albums_grid.set_activate_on_single_click(False)
        self.albums_scroll.set_child(self.albums_grid)
        scroll = self.albums_scroll
        box.append(scroll)
        self.stack.add_named(box, "albums")

    def _build_artists_page(self):
        box = self._page_list()
        self.artists_controls, self.artists_sort = self._build_grid_controls("artists")
        box.append(self.artists_controls)
        self.artists_empty = Adw.StatusPage(icon_name="avatar-default-symbolic", title="No artists yet",
                                            description="Artists appear after Sonora indexes your local music.")
        self.artists_empty.set_vexpand(True)
        box.append(self.artists_empty)
        self.artists_scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.artists_grid = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, min_children_per_line=2,
                                        max_children_per_line=7, row_spacing=18, column_spacing=14)
        self.artists_grid.set_homogeneous(True)
        self.artists_scroll.set_child(self.artists_grid)
        scroll = self.artists_scroll
        box.append(scroll)
        self.stack.add_named(box, "artists")

    def _build_grid_controls(self, kind):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        sort = Gtk.DropDown.new_from_strings(["Name", "Recently added", "Year"])
        sort.set_tooltip_text("Sort collection")
        sort.connect("notify::selected", lambda dropdown, _pspec, k=kind:
                      self._set_grid_sort(k, dropdown.get_selected()))
        bar.append(sort)
        letters = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        for letter in ("#", *"ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
            button = Gtk.Button(label=letter)
            button.add_css_class("flat")
            button.connect("clicked", lambda _button, k=kind, value=letter:
                           self._set_grid_letter(k, "#" if value == "#" else value))
            letters.append(button)
        letter_scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
                                           vscrollbar_policy=Gtk.PolicyType.NEVER)
        letter_scroll.set_child(letters)
        letter_scroll.set_hexpand(True)
        bar.append(letter_scroll)
        return bar, sort

    def _page_list(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        return box

    def _build_settings_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        page.set_margin_start(24)
        page.set_margin_end(24)
        page.set_margin_top(24)
        page.set_margin_bottom(24)
        page.set_halign(Gtk.Align.CENTER)

        appearance_group = Adw.PreferencesGroup(title="Appearance")
        appearance = Adw.ComboRow(title="Color scheme")
        appearance.set_model(Gtk.StringList.new(["Follow system", "Dark", "Light"]))
        appearance.set_selected(0)
        appearance.connect("notify::selected", self._on_color_scheme_changed)
        appearance_group.add(appearance)
        page.append(appearance_group)

        folders_group = Adw.PreferencesGroup(title="Music folders", description="Removing a folder from Sonora never deletes files.")
        folders_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.settings_add_button = Gtk.Button(label="Add folder")
        self.settings_add_button.add_css_class("suggested-action")
        self.settings_add_button.connect("clicked", self._choose_folder)
        folders_bar.append(self.settings_add_button)
        self.rescan_button = Gtk.Button(label="Rescan")
        self.rescan_button.connect("clicked", lambda *_: self.library.scan_all())
        folders_bar.append(self.rescan_button)
        self.cancel_button = Gtk.Button(label="Cancel scan")
        self.cancel_button.connect("clicked", lambda *_: self.library.cancel_scan())
        folders_bar.append(self.cancel_button)
        folders_group.add(folders_bar)
        self.folder_rows = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.folder_rows.add_css_class("boxed-list")
        folders_group.add(self.folder_rows)
        page.append(folders_group)

        exceptions_group = Adw.PreferencesGroup(
            title="Artist name exceptions",
            description="Keep names containing artist separators together. Enter one name per line.")
        self.artist_exceptions = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.artist_exceptions.set_monospace(True)
        self.artist_exceptions.set_size_request(-1, 104)
        exception_scroll = Gtk.ScrolledWindow(min_content_height=108, max_content_height=150)
        exception_scroll.set_child(self.artist_exceptions)
        exceptions_group.add(exception_scroll)
        exception_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        save_exceptions = Gtk.Button(label="Save exceptions")
        save_exceptions.connect("clicked", self._save_artist_exceptions)
        exception_actions.append(save_exceptions)
        self.exception_status = Gtk.Label(xalign=0)
        self.exception_status.add_css_class("dim-label")
        exception_actions.append(self.exception_status)
        exceptions_group.add(exception_actions)
        page.append(exceptions_group)
        self.stack.add_named(Adw.Clamp(child=page, maximum_size=760), "settings")
        exception_buffer = self.artist_exceptions.get_buffer()
        exception_buffer.set_text("\n".join(self.library.database.artist_split_exceptions()))

    def _build_favorites_page(self):
        page = self._page_list()
        self.favorites_page = page
        self.favorites_empty = Adw.StatusPage(icon_name="starred-symbolic", title="No favorites yet",
                                              description="Mark tracks with a heart to keep them here.")
        self.favorites_empty.set_vexpand(True)
        page.append(self.favorites_empty)
        self.favorites_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.favorites_list.add_css_class("boxed-list")
        self.favorites_list.connect("row-activated", self._activate_track_row)
        page.append(self.favorites_list)
        self.stack.add_named(page, "favorites")

    def _refresh_favorites_page(self):
        if not hasattr(self, "favorites_list"):
            return
        tracks = self.library.database.favorites()
        self._clear_list(self.favorites_list)
        self.favorites_empty.set_visible(not tracks)
        self.favorites_list.set_visible(bool(tracks))
        for track in tracks:
            self.favorites_list.append(self._track_row(track, tracks))

    def _refresh_playlist_nav(self):
        if not hasattr(self, "nav_list") or not hasattr(self, "playlist_nav_header"):
            return
        playlists = self.library.database.playlists()
        playlist_ids = {playlist["id"] for playlist in playlists}
        for playlist_id, row in list(self._playlist_nav_rows.items()):
            if playlist_id not in playlist_ids:
                self.nav_list.remove(row)
                del self._playlist_nav_rows[playlist_id]
        self.playlist_nav_header.set_visible(bool(playlists))
        for playlist in playlists:
            row = self._playlist_nav_rows.get(playlist["id"])
            if row is None:
                row = Adw.ActionRow(title=playlist["name"])
                row.set_activatable(True)
                row.add_prefix(Gtk.Image.new_from_icon_name("view-list-symbolic"))
                row.sonora_page = f"playlist:{playlist['id']}"
                self.nav_list.append(row)
                self._playlist_nav_rows[playlist["id"]] = row
            row.set_title(playlist["name"])
            row.set_subtitle(f"{playlist['track_count']} songs")

    def _ask_text(self, title, initial, callback, placeholder=""):
        dialog = Gtk.Dialog(title=title, transient_for=self, modal=True)
        dialog.set_default_size(440, -1)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Save", Gtk.ResponseType.ACCEPT)
        dialog.set_default_response(Gtk.ResponseType.ACCEPT)
        entry = Gtk.Entry(text=initial or "", placeholder_text=placeholder)
        entry.set_activates_default(True)
        entry.set_margin_top(12)
        entry.set_margin_bottom(12)
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        dialog.get_content_area().append(entry)
        dialog.connect("response", lambda current, response:
                       (callback(entry.get_text()) if response == Gtk.ResponseType.ACCEPT else None,
                        current.destroy()))
        dialog.present()

    def _confirm(self, title, message, callback):
        dialog = Gtk.Dialog(title=title, transient_for=self, modal=True)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Delete", Gtk.ResponseType.ACCEPT)
        label = Gtk.Label(label=message, wrap=True, xalign=0)
        label.set_margin_top(18)
        label.set_margin_bottom(18)
        label.set_margin_start(18)
        label.set_margin_end(18)
        dialog.get_content_area().append(label)
        dialog.connect("response", lambda current, response:
                       (callback() if response == Gtk.ResponseType.ACCEPT else None, current.destroy()))
        dialog.present()

    def _create_playlist_dialog(self, *_args, tracks=None):
        selected_tracks = list(tracks or [])
        self._ask_text("Create playlist", "", lambda name: self._create_playlist(name, selected_tracks),
                       "Playlist name")

    def _create_playlist(self, name, tracks=()):
        try:
            playlist_id = self.library.database.create_playlist(name)
        except Exception as error:
            self._playback_error(f"Could not create playlist: {error}")
            return
        for track in tracks:
            if track.id:
                self.library.database.add_playlist_track(playlist_id, track.id)
        self._refresh_playlist_nav()
        row = self._playlist_nav_rows.get(playlist_id)
        if row:
            self.nav_list.select_row(row)
        else:
            self._open_playlist(playlist_id)

    def _open_playlist(self, playlist_id):
        playlist = next((row for row in self.library.database.playlists() if row["id"] == playlist_id), None)
        if not playlist:
            self._refresh_playlist_nav()
            return
        tracks = self.library.database.playlist_tracks(playlist_id)
        self._open_detail("playlist", playlist["name"], tracks, entity_id=playlist_id)

    def _rename_playlist(self, playlist_id, old_name):
        self._ask_text("Rename playlist", old_name, lambda name: self._apply_playlist_rename(playlist_id, name),
                       "Playlist name")

    def _apply_playlist_rename(self, playlist_id, name):
        try:
            self.library.database.rename_playlist(playlist_id, name)
        except Exception as error:
            self._playback_error(f"Could not rename playlist: {error}")
            return
        self._refresh_playlist_nav()
        cleaned = " ".join(name.split())
        self.header_title.set_text(cleaned)
        if hasattr(self, "_detail_heading"):
            self._detail_heading.set_text(cleaned)

    def _delete_playlist(self, playlist_id, name):
        def delete():
            self.library.database.delete_playlist(playlist_id)
            self._refresh_playlist_nav()
            self._go_back()
        self._confirm("Delete playlist?", f"Delete ‘{name}’ and its saved track order? Your music files will stay untouched.", delete)

    def _add_to_playlist(self, playlist_id, tracks):
        tracks = list(tracks)
        existing = {track.id for track in self.library.database.playlist_tracks(playlist_id)}
        added = 0
        for track in tracks:
            if track.id and track.id not in existing:
                self.library.database.add_playlist_track(playlist_id, track.id)
                existing.add(track.id)
                added += 1
        self._refresh_playlist_nav()
        playlist = next((item for item in self.library.database.playlists() if item["id"] == playlist_id), None)
        name = playlist["name"] if playlist else "playlist"
        self._playback_error(f"Added {added} {('song' if added == 1 else 'songs')} to {name}.")

    def _import_m3u_dialog(self, *_args):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Import M3U playlist")
        dialog.open(self, None, self._m3u_opened)

    def _m3u_opened(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file and file.get_path():
                self._import_m3u(Path(file.get_path()))
        except GLib.Error as error:
            if not error.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
                self._playback_error(f"Could not import playlist: {error.message}")

    def _import_m3u(self, path):
        try:
            lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
            by_path = {str(Path(track.path).resolve()): track for track in self.library.tracks}
            tracks = []
            for line in lines:
                value = line.strip()
                if not value or value.startswith("#"):
                    continue
                if value.startswith("file:"):
                    file = Gio.File.new_for_uri(value)
                    value = file.get_path() or ""
                elif not Path(value).is_absolute():
                    value = str(path.parent / value)
                track = by_path.get(str(Path(value).resolve()))
                if track and all(existing.id != track.id for existing in tracks):
                    tracks.append(track)
            name = path.stem
            used = {playlist["name"].casefold() for playlist in self.library.database.playlists()}
            base = name or "Imported playlist"
            name = base
            suffix = 2
            while name.casefold() in used:
                name = f"{base} ({suffix})"
                suffix += 1
            playlist_id = self.library.database.create_playlist(name)
            for track in tracks:
                self.library.database.add_playlist_track(playlist_id, track.id)
            self._refresh_playlist_nav()
            if tracks:
                self._open_playlist(playlist_id)
            skipped = max(0, sum(1 for line in lines if line.strip() and not line.lstrip().startswith("#")) - len(tracks))
            self._playback_error(f"Imported {len(tracks)} songs into {name}; skipped {skipped} unavailable entries.")
        except (OSError, UnicodeError, ValueError) as error:
            self._playback_error(f"Could not import playlist: {error}")

    def _export_m3u_dialog(self, playlist_id):
        playlist = next((row for row in self.library.database.playlists() if row["id"] == playlist_id), None)
        if not playlist:
            return
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Export playlist")
        dialog.set_initial_name(f"{playlist['name']}.m3u")
        dialog.save(self, None, lambda source, result: self._m3u_saved(source, result, playlist_id))

    def _m3u_saved(self, dialog, result, playlist_id):
        try:
            file = dialog.save_finish(result)
            if file and file.get_path():
                tracks = self.library.database.playlist_tracks(playlist_id)
                lines = ["#EXTM3U"]
                for track in tracks:
                    lines.extend((f"#EXTINF:{max(0, track.duration_ms // 1000)},{track.title} - {track.display_artist}",
                                  track.path))
                Path(file.get_path()).write_text("\n".join(lines) + "\n", encoding="utf-8")
                self._playback_error(f"Exported {len(tracks)} songs.")
        except (GLib.Error, OSError) as error:
            if not isinstance(error, GLib.Error) or not error.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
                self._playback_error(f"Could not export playlist: {error}")

    def _toggle_favorite(self, track, favorite=None):
        if not track or not track.id:
            return
        current = self.library.database.is_favorite(track.id)
        desired = not current if favorite is None else bool(favorite)
        if current == desired:
            return
        self.library.database.favorite_track(track.id, desired)
        self._refresh_listen()
        self._refresh_favorites_page()
        if hasattr(self, "playback"):
            self._sync_player()

    def _favorite_button(self, track):
        button = Gtk.ToggleButton()
        button.add_css_class("flat")
        button.set_sensitive(bool(track.id))
        active = bool(track.id and self.library.database.is_favorite(track.id))
        button.set_active(active)
        button.set_label("♥" if active else "♡")
        button.set_tooltip_text("Remove from favorites" if active else "Add to favorites")
        button.connect("toggled", lambda control: self._favorite_button_toggled(control, track))
        return button

    def _favorite_button_toggled(self, button, track):
        self._toggle_favorite(track, button.get_active())

    def _build_player(self):
        self.player_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.player_bar.set_margin_start(10)
        self.player_bar.set_margin_end(10)
        self.player_bar.set_margin_top(8)
        self.player_bar.set_margin_bottom(8)
        self.player_bar.add_css_class("sonora-player")
        self.cover = Gtk.Image.new_from_icon_name("audio-x-generic-symbolic")
        self.cover.set_pixel_size(44)
        self.cover.set_size_request(48, 48)
        self.cover.add_css_class("sonora-artwork-small")
        self.cover.set_overflow(Gtk.Overflow.HIDDEN)
        self.cover_button = Gtk.Button(child=self.cover)
        self.cover_button.add_css_class("flat")
        self.cover_button.set_tooltip_text("Open Now Playing")
        self.cover_button.connect("clicked", lambda *_: self._open_now_playing())
        self.player_bar.append(self.cover_button)
        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        details.set_size_request(148, -1)
        self.player_details = details
        self.track_title = Gtk.Button(label="Nothing playing")
        self.track_title.add_css_class("flat")
        self.track_title.set_halign(Gtk.Align.START)
        self.track_title.connect("clicked", lambda *_: self._open_now_playing())
        self.track_title_label = Gtk.Label(label="Nothing playing", xalign=0, ellipsize=3)
        self.track_title.set_child(self.track_title_label)
        self.track_title_label.add_css_class("heading")
        self.track_artist = Gtk.Button()
        self.track_artist.add_css_class("flat")
        self.track_artist.add_css_class("dim-label")
        self.track_artist.set_halign(Gtk.Align.START)
        self.track_artist_label = Gtk.Label(label="Add a folder or choose a song", xalign=0, ellipsize=3)
        self.track_artist.set_child(self.track_artist_label)
        self.track_artist.connect("clicked", lambda *_: self._open_current_artist())
        details.append(self.track_title)
        details.append(self.track_artist)
        self.track_album = Gtk.Button()
        self.track_album.add_css_class("flat")
        self.track_album.add_css_class("dim-label")
        self.track_album.set_halign(Gtk.Align.START)
        self.track_album_label = Gtk.Label(label="", xalign=0, ellipsize=3)
        self.track_album.set_child(self.track_album_label)
        self.track_album.connect("clicked", lambda *_: self._album_for_track(self.playback.current_track)
                                 if self.playback.current_track else None)
        details.append(self.track_album)
        self.player_bar.append(details)
        self.current_favorite_button = Gtk.ToggleButton()
        self.current_favorite_button.set_tooltip_text("Add to favorites")
        self.current_favorite_button.connect("toggled", self._current_favorite_toggled)
        self.player_bar.append(self.current_favorite_button)

        self.prev_button = Gtk.Button.new_from_icon_name("media-skip-backward-symbolic")
        self.prev_button.set_tooltip_text("Previous track")
        self.prev_button.connect("clicked", lambda *_: self.playback.previous())
        self.player_bar.append(self.prev_button)
        self.play_button = Gtk.Button.new_from_icon_name("media-playback-start-symbolic")
        self.play_button.add_css_class("circular")
        self.play_button.set_tooltip_text("Play or pause")
        self.play_button.connect("clicked", lambda *_: self.playback.toggle())
        self.player_bar.append(self.play_button)
        self.next_button = Gtk.Button.new_from_icon_name("media-skip-forward-symbolic")
        self.next_button.set_tooltip_text("Next track")
        self.next_button.connect("clicked", lambda *_: self.playback.next())
        self.player_bar.append(self.next_button)

        self.shuffle_button = Gtk.ToggleButton()
        self.shuffle_button.set_icon_name("media-playlist-shuffle-symbolic")
        self.shuffle_button.set_tooltip_text("Shuffle queue")
        self.shuffle_button.connect("toggled", lambda button: self.playback.set_shuffle(button.get_active()))
        self.player_bar.append(self.shuffle_button)
        self.repeat_button = Gtk.Button.new_from_icon_name("media-playlist-repeat-symbolic")
        self.repeat_button.set_tooltip_text("Repeat off · click to change")
        self.repeat_button.connect("clicked", self._cycle_repeat)
        self.player_bar.append(self.repeat_button)

        self.queue_button = Gtk.MenuButton(label="Queue")
        self.queue_button.set_tooltip_text("Show play queue")
        self.queue_popover = Gtk.Popover()
        self.queue_popover.set_autohide(True)
        self.queue_button.set_popover(self.queue_popover)
        self.player_bar.append(self.queue_button)

        self.position_label = Gtk.Label(label="0:00", css_classes=["numeric"])
        self.position_button = Gtk.Button(child=self.position_label)
        self.position_button.add_css_class("flat")
        self.position_button.set_tooltip_text("Click to show remaining time")
        self.position_button.connect("clicked", self._toggle_time_display)
        self.player_bar.append(self.position_button)
        self.seek_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 1000)
        self.seek_scale.set_draw_value(False)
        self.seek_scale.set_hexpand(True)
        self.seek_scale.set_size_request(110, 34)
        self.seek_scale.connect("change-value", self._seek_to)
        self.seek_scale.add_controller(self._seek_motion_controller())
        self.player_bar.append(self.seek_scale)
        self.duration_label = Gtk.Label(label="0:00", css_classes=["numeric", "dim-label"])
        self.player_bar.append(self.duration_label)

        self.volume_button = Gtk.ToggleButton()
        self.volume_button.set_child(Gtk.Image.new_from_icon_name("audio-volume-high-symbolic"))
        self.volume_button.set_tooltip_text("Mute or unmute")
        self.volume_button.connect("toggled", self._mute_toggled)
        self.player_bar.append(self.volume_button)
        self.volume_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 0.05)
        self.volume_scale.set_draw_value(False)
        self.volume_scale.set_value(self.playback.volume)
        self.volume_scale.set_size_request(68, 30)
        self.volume_scale.set_tooltip_text("Volume")
        self.volume_scale.connect("value-changed", self._volume_changed)
        self.player_bar.append(self.volume_scale)

    def _restore_playback_state(self):
        raw = self.library.database.setting("playback_state", "")
        if not raw:
            return
        try:
            state = json.loads(raw)
            by_path = {track.path: track for track in self.library.tracks}
            queue = [by_path[path] for path in state.get("queue", []) if path in by_path]
            self.playback.restore_state(queue, state.get("position_ms", 0), state.get("volume", 0.8),
                                        state.get("muted", False), state.get("shuffle", False),
                                        state.get("repeat", "None"))
        except (TypeError, ValueError, KeyError):
            self.library.database.set_setting("playback_state", "")

    def _persist_playback_state(self):
        state = {
            "queue": [track.path for track in self.playback.queue],
            "position_ms": self.playback.position_us // 1000 if self.playback.current_track else 0,
            "volume": self.playback.volume,
            "muted": self.playback.muted,
            "shuffle": self.playback.shuffle_enabled,
            "repeat": self.playback.loop_status,
        }
        self.library.database.set_setting("playback_state", json.dumps(state, separators=(",", ":")))

    def _playback_error(self, message):
        if hasattr(self, "toast_overlay"):
            self.toast_overlay.add_toast(Adw.Toast.new(message))
        else:
            self._pending_playback_errors.append(message)

    def _record_listened_time(self, session_id, listened_ms):
        if self.library.database.add_listened_time(session_id, listened_ms):
            if hasattr(self, "home_shelves"):
                self._refresh_listen()

    def _finish_playback_session(self, session_id, reason):
        if self.library.database.finish_playback(session_id, reason):
            if hasattr(self, "home_shelves"):
                self._refresh_listen()

    def _seek_motion_controller(self):
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._seek_hover)
        return motion

    def _seek_hover(self, _controller, x, _y):
        duration = self.playback.duration_us // 1000
        width = self.seek_scale.get_width()
        if duration and width > 0:
            fraction = min(1.0, max(0.0, x / width))
            self.seek_scale.set_tooltip_text(self._format_time(int(duration * fraction)))

    def _toggle_time_display(self, *_args):
        self._show_remaining = not self._show_remaining
        self.position_button.set_tooltip_text("Click to show elapsed time" if self._show_remaining
                                              else "Click to show remaining time")
        self._tick()

    def _mute_toggled(self, button):
        self.playback.set_muted(button.get_active())

    def _cycle_repeat(self, *_args):
        cycle = {"None": "Playlist", "Playlist": "Track", "Track": "None"}
        self.playback.set_loop_status(cycle[self.playback.loop_status])

    def _action_menu_button(self, actions, tooltip="More options"):
        menu = Gtk.Popover()
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        content.set_margin_top(6)
        content.set_margin_bottom(6)
        content.set_margin_start(6)
        content.set_margin_end(6)
        for title, callback in actions:
            if title is None:
                content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
                continue
            action = Gtk.Button(label=title)
            action.add_css_class("flat")
            action.connect("clicked", lambda _button, cb=callback, pop=menu: (pop.popdown(), cb()))
            content.append(action)
        menu.set_child(content)
        button = Gtk.MenuButton(icon_name="view-more-symbolic", popover=menu)
        button.set_tooltip_text(tooltip)
        return button

    def _playlist_actions(self, tracks):
        actions = []
        playlists = self.library.database.playlists()
        if playlists:
            actions.extend((f"Add to {playlist['name']}",
                            lambda pid=playlist["id"], items=list(tracks): self._add_to_playlist(pid, items))
                           for playlist in playlists)
        actions.append(("New playlist…", lambda: self._create_playlist_dialog(tracks=list(tracks))))
        return actions

    def _queue_actions(self, track):
        actions = [
            ("Play next", lambda: self.playback.play_next(track)),
            ("Add to queue", lambda: self.playback.add_to_queue(track)),
        ]
        if track.id:
            actions.extend([
                (None, None),
                (("Remove from favorites" if self.library.database.is_favorite(track.id) else "Add to favorites"),
                 lambda: self._toggle_favorite(track)),
            ])
            actions.extend(self._playlist_actions([track]))
        if track.album and self._album_group_for_track(track):
            actions.append((None, None))
            actions.append(("Go to album", lambda: self._album_for_track(track)))
        artist_name = track.primary_artist or track.display_artist
        if self._artist_tracks(artist_name):
            actions.append(("Go to artist", lambda: self._open_artist(artist_name, self._artist_tracks(artist_name))))
        actions.append((None, None))
        actions.append(("Show in Files", lambda: self._show_in_files(track)))
        if track.id:
            actions.append(("Edit info…", lambda: self._edit_track_info(track)))
        return self._action_menu_button(actions)

    def _collection_actions(self, tracks, kind, title, subtitle):
        tracks = list(tracks)
        actions = [
            ("Play next", lambda: self.playback.play_next(tracks)),
            ("Add to queue", lambda: self.playback.add_to_queue(tracks)),
            (None, None),
        ]
        actions.extend(self._playlist_actions(tracks))
        if tracks:
            actions.append((None, None))
            if kind == "albums":
                artist_name = subtitle or tracks[0].album_artist or tracks[0].primary_artist
                artist_tracks = self._artist_tracks(artist_name)
                if artist_tracks:
                    actions.append(("Go to artist", lambda: self._open_artist(artist_name, artist_tracks)))
            else:
                actions.append(("Go to artist", lambda: self._open_artist(title, tracks)))
                album_groups = {}
                for track in tracks:
                    if track.album:
                        album_groups.setdefault(track.album, []).append(track)
                for album, album_tracks in sorted(album_groups.items(), key=lambda pair: self._sort_key(pair[0])):
                    album_artist = album_tracks[0].album_artist or title
                    actions.append((f"Go to album · {album}",
                                    lambda name=album, artist=album_artist, items=album_tracks:
                                    self._open_album(name, artist, items)))
            actions.extend([
                (None, None),
                ("Show in Files", lambda: self._show_in_files(tracks[0])),
                ("Edit info…", lambda: self._edit_collection_info(kind, tracks)),
            ])
        return self._action_menu_button(actions, f"More {kind} options")

    def _show_in_files(self, track):
        try:
            parent = Gio.File.new_for_path(track.path).get_parent()
            if parent:
                Gio.AppInfo.launch_default_for_uri(parent.get_uri(), None)
        except GLib.Error as error:
            self._playback_error(f"Could not open the music folder: {error.message}")

    def _edit_track_info(self, track):
        fields = (("title", "Title", track.title), ("artist", "Artist", track.display_artist),
                  ("album_artist", "Album artist", track.album_artist), ("album", "Album", track.album),
                  ("genre", "Genre", track.genre), ("composer", "Composer", track.composer),
                  ("year", "Year", str(track.year or "")), ("track_number", "Track number", str(track.track_number or "")),
                  ("disc_number", "Disc number", str(track.disc_number or "")))
        dialog = Gtk.Dialog(title="Edit track info", transient_for=self, modal=True)
        dialog.set_default_size(480, 560)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Save", Gtk.ResponseType.ACCEPT)
        grid = Gtk.Grid(column_spacing=12, row_spacing=8)
        grid.set_margin_top(16)
        grid.set_margin_bottom(16)
        grid.set_margin_start(16)
        grid.set_margin_end(16)
        entries = {}
        for row, (field, label, value) in enumerate(fields):
            name = Gtk.Label(label=label, xalign=0)
            entry = Gtk.Entry(text=value or "")
            entry.set_hexpand(True)
            grid.attach(name, 0, row, 1, 1)
            grid.attach(entry, 1, row, 1, 1)
            entries[field] = entry
        scroll = Gtk.ScrolledWindow(min_content_height=360, child=grid)
        dialog.get_content_area().append(scroll)
        def save(current, response):
            if response == Gtk.ResponseType.ACCEPT:
                for field, entry in entries.items():
                    value = entry.get_text().strip()
                    if field in {"year", "track_number", "disc_number"} and value:
                        try:
                            value = str(max(0, int(value)))
                        except ValueError:
                            continue
                    self.library.database.set_override(track.id, field, value)
                self.library.refresh()
            current.destroy()
        dialog.connect("response", save)
        dialog.present()

    def _edit_collection_info(self, kind, tracks):
        field = "album" if kind == "albums" else "artist"
        current_value = tracks[0].album if kind == "albums" else tracks[0].primary_artist or tracks[0].display_artist
        label = "Album title" if kind == "albums" else "Artist name"
        self._ask_text(f"Edit {label.casefold()}", current_value,
                       lambda value: self._apply_collection_info(field, value, tracks), label)

    def _apply_collection_info(self, field, value, tracks):
        if not value.strip():
            self._playback_error("The value cannot be empty.")
            return
        for track in tracks:
            if track.id:
                self.library.database.set_override(track.id, field, value.strip())
        self.library.refresh()

    def _refresh_queue_popover(self):
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        content.set_size_request(350, -1)
        heading = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = Gtk.Label(label="Play queue", xalign=0, css_classes=["title-3"])
        title.set_hexpand(True)
        heading.append(title)
        clear = Gtk.Button(label="Clear upcoming")
        clear.add_css_class("flat")
        clear.set_sensitive(len(self.playback.queue) > 1)
        clear.connect("clicked", lambda *_: self.playback.clear_upcoming())
        heading.append(clear)
        content.append(heading)
        if not self.playback.queue:
            content.append(Gtk.Label(label="Your queue is empty.", xalign=0, css_classes=["dim-label"]))
        for index, track in enumerate(self.playback.queue):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.set_margin_top(2)
            row.set_margin_bottom(2)
            row.set_tooltip_text("Now playing" if index == 0 else "Drag to reorder")
            row.append(self._cover_image(track.artwork_path, 36))
            labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            labels.set_hexpand(True)
            labels.append(Gtk.Label(label=track.title, xalign=0, ellipsize=3))
            labels.append(Gtk.Label(label=track.display_artist or "Unknown artist", xalign=0,
                                    ellipsize=3, css_classes=["dim-label", "caption"]))
            row.append(labels)
            if index == 0:
                row.append(Gtk.Label(label="Playing", css_classes=["accent", "caption"]))
            else:
                remove = Gtk.Button.new_from_icon_name("list-remove-symbolic")
                remove.set_tooltip_text("Remove from queue")
                remove.connect("clicked", lambda *_args, position=index: self.playback.remove_queue_item(position))
                row.append(remove)
                source = Gtk.DragSource()
                source.set_actions(Gdk.DragAction.MOVE)
                source.connect("prepare", lambda _source, _x, _y, position=index:
                               Gdk.ContentProvider.new_for_value(position))
                row.add_controller(source)
                target = Gtk.DropTarget.new(int, Gdk.DragAction.MOVE)
                target.connect("drop", lambda _target, value, _x, _y, dest=index:
                               self.playback.move_queue_item(value, dest))
                row.add_controller(target)
            content.append(row)
        self.queue_popover.set_child(content)

    def _on_nav_selected(self, _list, row):
        if row is None or not getattr(row, "sonora_page", None):
            return
        if _list is self.settings_list:
            self.nav_list.unselect_all()
        else:
            self.settings_list.unselect_all()
        if row.sonora_page.startswith("playlist:"):
            self._open_playlist(int(row.sonora_page.split(":", 1)[1]))
        else:
            self._show_page(row.sonora_page)

    def _update_back_button(self, *_args):
        if hasattr(self, "back_button"):
            detail_back = bool(self._detail_history)
            self.back_button.set_visible(detail_back or (self.split.get_collapsed() and self.split.get_show_content()))
            self.back_button.set_tooltip_text("Back to previous page" if detail_back else "Back to navigation")

    def _show_page(self, page: str):
        if page in {"listen", "songs", "albums", "artists", "favorites", "settings"}:
            for detail_name in self._detail_page_names:
                child = self.stack.get_child_by_name(detail_name)
                if child:
                    self.stack.remove(child)
            self._detail_page_names.clear()
            self._detail_indicators.clear()
            self._detail_scrolls.clear()
            self._detail_indicator_starts.clear()
            self._detail_page_name = None
            self._detail_history.clear()
        self._active_page = page
        titles = {"listen": "Listen Now", "songs": "Songs", "albums": "Albums", "artists": "Artists",
                  "favorites": "Favorites", "settings": "Settings"}
        self.header_title.set_text(titles.get(page, "Sonora"))
        self.stack.set_visible_child_name(page)
        if page in {"albums", "artists"}:
            self._render_collection_grid(page)
        self.search_entry.set_visible(page != "settings")
        if self.search_results.get_visible():
            self.search_results.popdown()
        if page == "listen" and self.split.get_collapsed():
            self.split.set_show_content(True)
        if page != "listen" and self.split.get_collapsed():
            self.split.set_show_content(True)

    def _on_search_changed(self, entry):
        self._refresh_songs()
        self._refresh_search_results(entry.get_text())

    def _on_search_activate(self, _entry):
        if self.search_results.get_visible():
            first = self.search_results_content.get_first_child()
            while first:
                if isinstance(first, Gtk.Button):
                    first.emit("clicked")
                    return
                first = first.get_next_sibling()
        self.search_results.popdown()
        self.nav_list.select_row(self.nav_list.get_row_at_index(1))

    def _refresh_search_results(self, query):
        self._clear_list(self.search_results_content)
        query = query.strip()
        if not query or self._active_page == "settings":
            self.search_results.popdown()
            return
        folded_query = self._fold(query)
        query_tokens = folded_query.split()
        tracks = [track for track in self.library.search(query) if all(token in self._fold(
            " ".join((track.title, track.display_artist, track.album, track.genre))) for token in query_tokens)]
        albums = [(title, artist, rows, folder) for title, artist, rows, folder in self.library.database.album_groups()
                  if all(token in self._fold(f"{title} {artist}") for token in query_tokens)]
        artists = [(name, rows) for name, rows in self.library.database.artist_groups()
                   if all(token in self._fold(name) for token in query_tokens)]
        found = False
        for label, items, opener in (
            ("Songs", tracks[:5], lambda item: self._play_specific(item, tracks)),
            ("Albums", albums[:4], lambda item: self._open_album(item[0], item[1], item[2])),
            ("Artists", artists[:4], lambda item: self._open_artist(item[0], item[1])),
        ):
            if not items:
                continue
            found = True
            heading = Gtk.Label(label=label, xalign=0, css_classes=["heading"])
            self.search_results_content.append(heading)
            for item in items:
                title = item.title if label == "Songs" else (item[0] if label == "Albums" else item[0])
                subtitle = item.display_artist if label == "Songs" else (item[1] if label == "Albums" else f"{len(item[1])} songs")
                button = Gtk.Button()
                button.add_css_class("flat")
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                if label == "Songs":
                    row.append(self._cover_image(item.artwork_path, 36))
                else:
                    rows = item[2] if label == "Albums" else item[1]
                    art = next((track.artwork_path for track in rows if track.artwork_path), "")
                    row.append(self._cover_image(art, 36, "avatar-default-symbolic" if label == "Artists" else "media-optical-symbolic"))
                labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
                name = Gtk.Label(label=title, xalign=0, ellipsize=3)
                name.add_css_class("heading")
                detail = Gtk.Label(label=subtitle or "Unknown artist", xalign=0, ellipsize=3)
                detail.add_css_class("dim-label")
                labels.append(name)
                labels.append(detail)
                row.append(labels)
                button.set_child(row)
                button.set_halign(Gtk.Align.FILL)
                button.connect("clicked", lambda _button, current=item, fn=opener: self._search_open(fn, current))
                self.search_results_content.append(button)
        if not found:
            label = Gtk.Label(label="No matching songs, albums, or artists", xalign=0)
            label.add_css_class("dim-label")
            self.search_results_content.append(label)
        self.search_results.popup()

    def _search_open(self, opener, item):
        self.search_results.popdown()
        opener(item)

    @staticmethod
    def _fold(value):
        decomposed = unicodedata.normalize("NFKD", str(value).casefold())
        return " ".join("".join(char for char in decomposed if not unicodedata.combining(char)).split())

    def _on_key_pressed(self, _controller, keyval, _keycode, state):
        control = bool(state & Gdk.ModifierType.CONTROL_MASK)
        focus = self.get_focus()
        editable = isinstance(focus, (Gtk.Entry, Gtk.TextView, Gtk.SpinButton))
        if not editable and keyval == Gdk.KEY_space:
            if self.playback.current_track:
                self.playback.toggle()
                return True
        if control and not editable and keyval in (Gdk.KEY_Left, Gdk.KEY_Right):
            (self.playback.previous if keyval == Gdk.KEY_Left else self.playback.next)()
            return True
        if not editable:
            if keyval == getattr(Gdk, "KEY_XF86AudioRaiseVolume", -1):
                self.playback.set_volume(self.playback.volume + 0.05)
                return True
            if keyval == getattr(Gdk, "KEY_XF86AudioLowerVolume", -1):
                self.playback.set_volume(self.playback.volume - 0.05)
                return True
            if keyval == getattr(Gdk, "KEY_XF86AudioMute", -1):
                self.playback.set_muted(not self.playback.muted)
                return True
        if self._active_page != "settings" and (control and keyval == Gdk.KEY_f or
                                                  keyval == Gdk.KEY_slash and not editable):
            self.search_entry.grab_focus()
            return True
        if keyval in (Gdk.KEY_Escape, Gdk.KEY_Left) and (keyval == Gdk.KEY_Escape or state & Gdk.ModifierType.ALT_MASK):
            if self.search_results.get_visible():
                self.search_results.popdown()
                return True
            if self._detail_history:
                self._go_back()
                return True
        return False

    def _on_color_scheme_changed(self, row, _property):
        manager = Adw.StyleManager.get_default()
        manager.set_color_scheme((Adw.ColorScheme.DEFAULT, Adw.ColorScheme.PREFER_DARK, Adw.ColorScheme.PREFER_LIGHT)[row.get_selected()])

    def _choose_folder(self, *_args):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Choose a music folder")
        dialog.select_folder(self, None, self._folder_selected)

    def _folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder and folder.get_path():
                self.library.add_folder(folder.get_path())
        except GLib.Error as error:
            if error.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
                return
            self.library.error = error.message
            self._refresh()

    def _activate_track_row(self, _list, row):
        track = getattr(row, "sonora_track", None)
        if track:
            self.playback.play_track(track, getattr(row, "sonora_queue", self.library.tracks))

    def _play_specific(self, track, queue):
        self.playback.play_track(track, queue)

    def _refresh(self):
        if not hasattr(self, "stack"):
            return
        self._refresh_listen()
        self._refresh_songs()
        self._refresh_collections()
        self._refresh_folders()
        self._refresh_playlist_nav()
        self._refresh_favorites_page()
        self._sync_player()

    def _scan_progress_changed(self, current, total):
        if hasattr(self, "scan_status") and total:
            self.scan_status.set_text(f"Scanning {current} of {total} files…")
            self.scan_status.set_visible(True)
        if hasattr(self, "home_library_status"):
            self.home_library_status.set_text(f"Adding music · {current:,} of {total:,} files")
            self.home_library_status.set_visible(True)

    def _refresh_listen(self):
        tracks = self.library.tracks
        count = len(tracks)
        self.home_description.set_text("Your music, in one place." if not count else
                                       f"{count:,} local " + ("song" if count == 1 else "songs") + ". Ready when you are.")
        if self.library.error:
            status = self.library.error
        elif self.library.scanning:
            current, total = self.library.scan_progress
            status = f"Adding music · {current:,} of {total:,} files" if total else "Adding music to your library…"
        else:
            status = ""
        self.home_library_status.set_text(status)
        self.home_library_status.set_visible(bool(status))
        self.home_play_all.set_sensitive(bool(tracks) and not self.library.scanning)
        self.home_empty.set_visible(not tracks)
        self.home_shelves.set_visible(bool(tracks))
        if not tracks:
            for section in (self.home_jump, self.home_played, self.home_most_played, self.home_recent,
                            self.home_rediscover, self.home_random_albums):
                section["widget"].set_visible(False)
            return

        by_path = {track.path: track for track in tracks}
        recently_added = sorted(tracks, key=lambda track: (track.album.casefold(), track.track_number or 10_000,
                                                            track.title.casefold()))
        recently_added.sort(key=lambda track: track.first_added_at or "", reverse=True)
        recently_added = recently_added[:10]
        recent_paths = self.library.database.recently_played_paths(20)
        recently_played = [by_path[path] for path in recent_paths if path in by_path]
        most_played = sorted((track for track in tracks if track.play_count),
                             key=lambda track: (-track.play_count, track.title.casefold()))[:10]
        rediscover = self.library.database.rediscover_tracks(10)
        jump = self.playback.current_track
        if not jump:
            jump = next((by_path[path] for path in recent_paths if path in by_path), None)
        self._fill_home_track_section(self.home_jump, [jump] if jump else [])
        self._fill_home_track_section(self.home_played, recently_played[:10])
        self._fill_home_track_section(self.home_most_played, most_played)
        self._fill_home_track_section(self.home_recent, recently_added)
        self._fill_home_track_section(self.home_rediscover, rediscover)
        album_groups = self.library.database.album_groups()
        self._fill_home_album_section(self.home_random_albums,
                                      random.sample(album_groups, min(8, len(album_groups))))

    def _fill_home_track_section(self, section, tracks):
        self._clear_list(section["content"])
        for track in tracks:
            section["content"].append(self._home_track_card(track))
        section["widget"].set_visible(bool(tracks))

    def _fill_home_album_section(self, section, albums):
        self._clear_list(section["content"])
        for title, artist, tracks, _folder in albums:
            ordered = sorted(tracks, key=lambda track: (track.disc_number or 1,
                              track.track_number or 10_000, track.title.casefold()))
            section["content"].append(self._home_collection_card(
                title, artist, ordered, "media-optical-symbolic"))
        section["widget"].set_visible(bool(albums))

    def _home_track_card(self, track):
        shell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        shell.set_size_request(188, 242)
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.set_margin_start(8)
        card.set_margin_end(8)
        card.set_margin_top(8)
        card.set_margin_bottom(8)
        card.append(self._cover_image(track.artwork_path, 152))
        title = Gtk.Label(label=track.title, xalign=0, ellipsize=3, max_width_chars=24)
        title.add_css_class("heading")
        artist = Gtk.Label(label=track.display_artist, xalign=0, ellipsize=3, max_width_chars=24)
        artist.add_css_class("dim-label")
        card.append(title)
        card.append(artist)
        open_button = Gtk.Button(child=card)
        open_button.add_css_class("card")
        open_button.add_css_class("flat")
        open_button.set_tooltip_text(f"Open {track.album or track.title}")
        open_button.connect("clicked", lambda *_: self._open_track_context(track))
        shell.append(open_button)
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        actions.set_halign(Gtk.Align.END)
        play = Gtk.Button.new_from_icon_name("media-playback-start-symbolic")
        play.set_tooltip_text(f"Play {track.title}")
        play.connect("clicked", lambda *_: self._play_specific(track, self.library.tracks))
        actions.append(play)
        actions.append(self._favorite_button(track))
        actions.append(self._queue_actions(track))
        shell.append(actions)
        return shell

    def _home_collection_card(self, title, subtitle, tracks, icon):
        kind = "artists" if icon == "avatar-default-symbolic" else "albums"
        return self._collection_card(kind, title, subtitle, tracks, icon)

    def _collection_card(self, kind, title, subtitle, tracks, icon):
        card_shell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card_shell.set_size_request(188, 242)
        card_shell.add_css_class("collection-card")
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.set_margin_start(8)
        card.set_margin_end(8)
        card.set_margin_top(8)
        card.set_margin_bottom(8)
        artwork = next((track.artwork_path for track in tracks if track.artwork_path), "")
        card.append(self._cover_image(artwork, 152, icon))
        title_label = Gtk.Label(label=title, xalign=0, ellipsize=3, max_width_chars=24)
        title_label.add_css_class("heading")
        subtitle_label = Gtk.Label(label=subtitle, xalign=0, ellipsize=3, max_width_chars=24)
        subtitle_label.add_css_class("dim-label")
        card.append(title_label)
        card.append(subtitle_label)
        open_button = Gtk.Button(child=card)
        open_button.add_css_class("card")
        open_button.add_css_class("flat")
        open_button.set_tooltip_text(f"Open {title}")
        open_button.connect("clicked", lambda *_: self._open_artist(title, tracks) if kind == "artists"
                            else self._open_album(title, subtitle, tracks))
        card_shell.append(open_button)
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        actions.set_halign(Gtk.Align.END)
        play_button = Gtk.Button.new_from_icon_name("media-playback-start-symbolic")
        play_button.set_tooltip_text(f"Play {title}")
        play_button.connect("clicked", lambda *_: self._play_specific(tracks[0], tracks) if tracks else None)
        actions.append(play_button)
        actions.append(self._collection_actions(tracks, kind, title, subtitle))
        card_shell.append(actions)
        return card_shell

    def _navigate_to(self, page):
        row = self._nav_rows.get(page)
        if row:
            self.nav_list.select_row(row)

    def _refresh_songs(self):
        if not hasattr(self, "songs_list"):
            return
        self._song_refresh_generation += 1
        generation = self._song_refresh_generation
        self._clear_list(self.songs_list)
        tracks = self.library.search(self.search_entry.get_text()) if hasattr(self, "search_entry") else self.library.tracks
        GLib.idle_add(self._append_song_batch, generation, tracks, 0)
        if hasattr(self, "scan_status"):
            if self.library.error:
                status = self.library.error
            elif self.library.scanning:
                current, total = self.library.scan_progress
                status = f"Scanning {current} of {total} files…" if total else "Scanning local music…"
            else:
                status = self.library.status or (f"{len(self.library.tracks):,} songs" if self.library.tracks else "No music folders yet")
            self.scan_status.set_text(status)
            self.scan_status.set_visible(bool(status))

    def _append_song_batch(self, generation, tracks, offset):
        if generation != self._song_refresh_generation:
            return GLib.SOURCE_REMOVE
        end = min(offset + 24, len(tracks))
        for track in tracks[offset:end]:
            self.songs_list.append(self._track_row(track, tracks))
        if end < len(tracks):
            GLib.idle_add(self._append_song_batch, generation, tracks, end)
        return GLib.SOURCE_REMOVE

    def _track_row(self, track, queue=None):
        row = Gtk.ListBoxRow()
        row.set_activatable(True)
        # PyGObject 3.56+ intentionally disables GObject's legacy data API.
        row.sonora_track = track
        row.sonora_queue = list(queue or self.library.tracks)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        cover = self._cover_image(track.artwork_path, 40)
        box.append(cover)
        title = Gtk.Label(label=track.title, xalign=0, ellipsize=3)
        title.add_css_class("heading")
        title.set_hexpand(True)
        box.append(title)
        artist = self._link_button(track.display_artist or "Unknown artist", lambda: self._open_artist(
            track.primary_artist or track.display_artist, self._artist_tracks(track.primary_artist or track.display_artist)))
        artist.set_size_request(140, -1)
        artist.set_tooltip_text(track.display_artist or "Unknown artist")
        box.append(artist)
        album = self._link_button(track.album or "Unknown album", lambda: self._album_for_track(track))
        album.set_size_request(140, -1)
        album.set_sensitive(bool(track.album))
        album.set_tooltip_text(track.album or "Unknown album")
        box.append(album)
        duration = Gtk.Label(label=self._format_time(track.duration_ms), xalign=1)
        duration.add_css_class("numeric")
        duration.add_css_class("dim-label")
        duration.set_size_request(48, -1)
        box.append(duration)
        play = Gtk.Button.new_from_icon_name("media-playback-start-symbolic")
        play.set_tooltip_text(f"Play {track.title}")
        tracks_for_row = row.sonora_queue
        play.connect("clicked", lambda *_: self._play_specific(track, tracks_for_row))
        box.append(play)
        box.append(self._favorite_button(track))
        box.append(self._queue_actions(track))
        row.set_child(box)
        return row

    def _refresh_collections(self):
        self._collection_cache["albums"] = self.library.database.album_groups()
        self._collection_cache["artists"] = self.library.database.artist_groups()
        self.albums_empty.set_visible(not self._collection_cache["albums"])
        self.albums_scroll.set_visible(bool(self._collection_cache["albums"]))
        self.artists_empty.set_visible(not self._collection_cache["artists"])
        self.artists_scroll.set_visible(bool(self._collection_cache["artists"]))
        self._artist_track_map = {artist.casefold(): tracks for artist, tracks in self._collection_cache["artists"]}
        self._album_track_map = {track.path: (title, artist, tracks)
                                 for title, artist, tracks, _folder in self._collection_cache["albums"]
                                 for track in tracks}
        if self._active_page in {"albums", "artists"}:
            self._render_collection_grid(self._active_page)

    @staticmethod
    def _sort_key(value):
        value = SonoraWindow._fold(value)
        return value[4:] if value.startswith("the ") else value

    def _set_grid_sort(self, kind, selected):
        self._grid_sort[kind] = ("Name", "Recently added", "Year")[min(selected, 2)]
        self._render_collection_grid(kind)

    def _set_grid_letter(self, kind, letter):
        self._grid_letter[kind] = letter
        self._render_collection_grid(kind)

    def _render_collection_grid(self, kind):
        grid = self.albums_grid if kind == "albums" else self.artists_grid
        self._clear_list(grid)
        items = self._collection_cache[kind]
        if kind == "albums":
            name = lambda item: item[0]
            date = lambda item: max((track.first_seen_at for track in item[2]), default="")
            year = lambda item: max((track.year for track in item[2]), default=0)
            subtitle = lambda item: item[1]
            tracks_of = lambda item: item[2]
        else:
            name = lambda item: item[0]
            date = lambda item: max((track.first_seen_at for track in item[1]), default="")
            year = lambda item: max((track.year for track in item[1]), default=0)
            subtitle = lambda item: f"{len(item[1])} songs"
            tracks_of = lambda item: item[1]
        sort = self._grid_sort[kind]
        if sort == "Recently added":
            items = sorted(items, key=lambda item: (date(item), self._sort_key(name(item))), reverse=True)
        elif sort == "Year":
            items = sorted(items, key=lambda item: (year(item), self._sort_key(name(item))), reverse=True)
        else:
            items = sorted(items, key=lambda item: self._sort_key(name(item)))
        letter = self._grid_letter[kind]
        if letter:
            items = [item for item in items if (not self._sort_key(name(item))[:1].isalpha()
                     if letter == "#" else self._sort_key(name(item)).upper().startswith(letter))]
        self._grid_render_generation[kind] += 1
        generation = self._grid_render_generation[kind]
        GLib.idle_add(self._append_collection_grid_batch, kind, generation, items, 0)

    def _append_collection_grid_batch(self, kind, generation, items, offset):
        if generation != self._grid_render_generation[kind]:
            return GLib.SOURCE_REMOVE
        grid = self.albums_grid if kind == "albums" else self.artists_grid
        end = min(offset + 18, len(items))
        for item in items[offset:end]:
            if kind == "albums":
                title, artist, tracks, _folder = item
                subtitle = artist
            else:
                title, tracks = item
                subtitle = f"{len(tracks)} songs"
            icon = "media-optical-symbolic" if kind == "albums" else "avatar-default-symbolic"
            grid.append(self._collection_card(kind, title, subtitle, tracks, icon))
        if end < len(items):
            GLib.idle_add(self._append_collection_grid_batch, kind, generation, items, end)
        return GLib.SOURCE_REMOVE

    def _open_album(self, title, artist, tracks):
        if not tracks:
            return
        tracks = sorted(tracks, key=lambda track: (track.disc_number or 1, track.track_number or 10_000, track.title.casefold()))
        self._open_detail("album", title, tracks, artist)

    def _open_artist(self, name, tracks):
        if not tracks:
            return
        tracks = sorted(tracks, key=lambda track: (track.album.casefold(), track.disc_number or 1,
                                                   track.track_number or 10_000, track.title.casefold()))
        self._open_detail("artist", name, tracks)

    def _open_detail(self, kind, title, tracks, subtitle="", entity_id=None):
        scrolls = {"listen": self.listen_page, "songs": self.songs_scroll, "albums": self.albums_scroll,
                   "artists": self.artists_scroll, "favorites": self.favorites_page, "settings": None}
        if self._active_page in self._detail_scrolls:
            scroll = self._detail_scrolls[self._active_page]
        else:
            scroll = scrolls.get(self._active_page)
        adjustment = scroll.get_vadjustment().get_value() if scroll else 0
        sort = self._grid_sort.get(self._active_page, "Name")
        letter = self._grid_letter.get(self._active_page, "")
        previous_detail = self._detail_page_name
        self._detail_history.append((self._active_page, adjustment, sort, letter, previous_detail,
                                     self.header_title.get_text()))
        self._detail_page_name = f"detail-{kind}-{len(self._detail_history)}"
        self._active_playlist_id = entity_id if kind == "playlist" else None
        self._detail_indicator_starts[self._detail_page_name] = len(self._detail_indicators)
        page = self._page_list()
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        header.set_margin_bottom(12)
        header.append(self._cover_image(next((track.artwork_path for track in tracks if track.artwork_path), ""), 180,
                                        "avatar-default-symbolic" if kind == "artist" else "media-optical-symbolic"))
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        info.set_valign(Gtk.Align.CENTER)
        heading = Gtk.Label(label=title, xalign=0, wrap=True, css_classes=["title-1"])
        self._detail_heading = heading
        info.append(heading)
        if kind == "album":
            linked_artist_tracks = self._artist_tracks(subtitle)
            artist_link = self._link_button(subtitle or "Unknown artist", lambda: self._open_artist(
                subtitle, linked_artist_tracks), enabled=bool(linked_artist_tracks))
            info.append(artist_link)
            years = [track.year for track in tracks if track.year]
            summary = f"{years[0]} · " if years else ""
            total = sum(track.duration_ms for track in tracks)
            summary += f"{len(tracks)} songs · {self._format_time(total)}"
        elif kind == "artist":
            albums = {track.album for track in tracks if track.album}
            summary = f"{len(albums)} albums · {len(tracks)} songs"
        elif kind == "playlist":
            total = sum(track.duration_ms for track in tracks)
            summary = f"{len(tracks)} songs · {self._format_time(total)}"
        else:
            summary = f"{tracks[0].display_artist} · {tracks[0].album}" if tracks else "Nothing is playing"
        meta = Gtk.Label(label=summary, xalign=0, css_classes=["dim-label"])
        info.append(meta)
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        play = Gtk.Button(label="Play")
        play.add_css_class("suggested-action")
        play.set_sensitive(bool(tracks))
        play.connect("clicked", lambda *_: self._play_specific(tracks[0], tracks) if tracks else None)
        shuffle = Gtk.Button(label="Shuffle")
        shuffle.set_sensitive(bool(tracks))
        shuffle.connect("clicked", lambda *_: self._shuffle_tracks(tracks))
        actions.append(play)
        actions.append(shuffle)
        if kind == "playlist":
            rename = Gtk.Button(label="Rename")
            rename.connect("clicked", lambda *_: self._rename_playlist(entity_id, self.header_title.get_text()))
            export = Gtk.Button(label="Export M3U")
            export.connect("clicked", lambda *_: self._export_m3u_dialog(entity_id))
            delete = Gtk.Button(label="Delete")
            delete.add_css_class("destructive-action")
            delete.connect("clicked", lambda *_: self._delete_playlist(entity_id, self.header_title.get_text()))
            actions.append(rename)
            actions.append(export)
            actions.append(delete)
        info.append(actions)
        header.append(info)
        page.append(header)
        if kind == "artist":
            album_map = {}
            for track in tracks:
                if track.album:
                    album_map.setdefault(track.album, []).append(track)
            if album_map:
                page.append(Gtk.Label(label="Albums", xalign=0, css_classes=["title-2"]))
                album_grid = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, min_children_per_line=2,
                                         max_children_per_line=6, row_spacing=12, column_spacing=12)
                album_grid.set_homogeneous(True)
                for album, album_tracks in sorted(album_map.items(), key=lambda pair: self._sort_key(pair[0])):
                    album_artist = album_tracks[0].album_artist or title
                    album_grid.append(self._collection_card("albums", album, album_artist, album_tracks,
                                                            "media-optical-symbolic"))
                page.append(album_grid)
        songs_heading = Gtk.Label(label="All songs" if kind == "artist" else ("Now playing" if kind == "now-playing" else "Tracks"), xalign=0,
                                  css_classes=["title-2"])
        page.append(songs_heading)
        list_box = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        list_box.add_css_class("boxed-list")
        if kind == "playlist":
            list_box.set_placeholder(Gtk.Label(label="This playlist is empty.", css_classes=["dim-label"]))
        appears = []
        if kind == "artist":
            appears = [track for track in tracks if track.primary_artist.casefold() != title.casefold()
                       and (track.album_artist or "").casefold() != title.casefold()
                       and track.display_artist and title.casefold() in track.display_artist.casefold()]
        own_tracks = [track for track in tracks if track not in appears]
        if kind == "playlist":
            self._active_playlist_rows = {}
        for track in own_tracks:
            row = self._detail_track_row(track, own_tracks, show_disc=(kind == "album"),
                                         playlist_id=entity_id if kind == "playlist" else None)
            list_box.append(row)
            if kind == "playlist":
                self._active_playlist_rows[track.id] = row
        page.append(list_box)
        if kind == "playlist":
            self._active_playlist_list = list_box
            self._active_playlist_summary = meta
        if kind == "artist" and appears:
            page.append(Gtk.Label(label="Appears on", xalign=0, css_classes=["title-2"]))
            appears_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
            appears_list.add_css_class("boxed-list")
            for track in appears:
                appears_list.append(self._detail_track_row(track, appears))
            page.append(appears_list)
        detail_scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER,
                                           vscrollbar_policy=Gtk.PolicyType.AUTOMATIC, child=page)
        self.stack.add_named(detail_scroll, self._detail_page_name)
        self._detail_page_names.append(self._detail_page_name)
        self._detail_scrolls[self._detail_page_name] = detail_scroll
        self.stack.set_visible_child(detail_scroll)
        self._active_page = self._detail_page_name
        self.header_title.set_text(title)
        self._update_back_button()

    def _detail_track_row(self, track, queue, show_disc=False, playlist_id=None):
        row = Gtk.ListBoxRow()
        row.set_activatable(True)
        row.sonora_track = track
        line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        line.set_margin_start(8)
        line.set_margin_end(8)
        line.set_margin_top(4)
        line.set_margin_bottom(4)
        current = self.playback.current_track is not None and self.playback.current_track.path == track.path
        prefix_text = (f"{track.disc_number or 1}.{track.track_number or '–'}" if show_disc
                       else str(track.track_number or ""))
        number = Gtk.Label(label="♫" if current else prefix_text, width_chars=5, xalign=1)
        number.add_css_class("dim-label" if not current else "accent")
        number.sonora_track_path = track.path
        number.sonora_track_number = prefix_text
        self._detail_indicators.append(number)
        line.append(number)
        line.append(self._cover_image(track.artwork_path, 40))
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        labels.set_hexpand(True)
        labels.append(Gtk.Label(label=track.title, xalign=0, ellipsize=3, css_classes=["heading"]))
        credits = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        artist_button = self._link_button(track.display_artist or "Unknown artist", lambda: self._open_artist(
            track.primary_artist or track.display_artist, self._artist_tracks(track.primary_artist or track.display_artist)))
        artist_button.set_sensitive(bool(self._artist_tracks(track.primary_artist or track.display_artist)))
        credits.append(artist_button)
        if track.album:
            credits.append(Gtk.Label(label="·", css_classes=["dim-label"]))
            album_button = self._link_button(track.album, lambda: self._album_for_track(track),
                                             enabled=bool(self._album_group_for_track(track)))
            credits.append(album_button)
        labels.append(credits)
        line.append(labels)
        line.append(Gtk.Label(label=self._format_time(track.duration_ms), css_classes=["dim-label", "numeric"]))
        play = Gtk.Button.new_from_icon_name("media-playback-start-symbolic")
        play.set_tooltip_text(f"Play {track.title}")
        play.connect("clicked", lambda *_: self._play_specific(track, queue))
        line.append(play)
        line.append(self._favorite_button(track))
        line.append(self._queue_actions(track))
        if playlist_id is not None:
            remove = Gtk.Button.new_from_icon_name("list-remove-symbolic")
            remove.set_tooltip_text("Remove from playlist")
            remove.connect("clicked", lambda *_: self._remove_from_playlist(playlist_id, track.id))
            line.append(remove)
            source = Gtk.DragSource()
            source.set_actions(Gdk.DragAction.MOVE)
            source.connect("prepare", lambda _source, _x, _y, track_id=track.id:
                           Gdk.ContentProvider.new_for_value(track_id))
            row.add_controller(source)
            target = Gtk.DropTarget.new(int, Gdk.DragAction.MOVE)
            target.connect("drop", lambda _target, track_id, _x, _y, destination=track.id:
                           self._reorder_playlist_track(playlist_id, track_id, destination))
            row.add_controller(target)
        row.set_child(line)
        row.connect("activate", lambda *_: self._play_specific(track, queue))
        return row

    def _reorder_playlist_track(self, playlist_id, source_id, destination_id):
        if source_id == destination_id or not self.library.database.move_playlist_track(
                playlist_id, source_id, destination_id):
            return False
        ordered = self.library.database.playlist_tracks(playlist_id)
        rows = self._active_playlist_rows
        if playlist_id == self._active_playlist_id:
            self._order_playlist_widgets(ordered)
        return True

    def _order_playlist_widgets(self, tracks):
        for row in self._active_playlist_rows.values():
            self._active_playlist_list.remove(row)
        for track in tracks:
            row = self._active_playlist_rows.get(track.id)
            if row:
                self._active_playlist_list.append(row)

    def _remove_from_playlist(self, playlist_id, track_id):
        self.library.database.remove_playlist_track(playlist_id, track_id)
        if playlist_id != self._active_playlist_id:
            self._refresh_playlist_nav()
            return
        row = self._active_playlist_rows.pop(track_id, None)
        if row:
            self._active_playlist_list.remove(row)
        tracks = self.library.database.playlist_tracks(playlist_id)
        self._order_playlist_widgets(tracks)
        total = sum(track.duration_ms for track in tracks)
        self._active_playlist_summary.set_text(f"{len(tracks)} songs · {self._format_time(total)}")
        self._refresh_playlist_nav()

    def _album_for_track(self, track):
        group = self._album_group_for_track(track)
        if group:
            self._open_album(*group)

    def _album_group_for_track(self, track):
        if not track:
            return None
        return self._album_track_map.get(track.path)

    def _artist_tracks(self, name):
        return self._artist_track_map.get((name or "").casefold(), [])

    @staticmethod
    def _link_button(text, callback, enabled=True):
        label = Gtk.Label(label=text, xalign=0, ellipsize=3)
        button = Gtk.Button(child=label)
        button.add_css_class("flat")
        button.add_css_class("link")
        button.set_halign(Gtk.Align.START)
        button.set_sensitive(enabled)
        button.connect("clicked", lambda *_: callback())
        return button

    def _shuffle_tracks(self, tracks):
        if tracks:
            self.playback.play_track(tracks[0], tracks)
            self.playback.set_shuffle(True)

    def _go_back(self):
        if self.search_results.get_visible():
            self.search_results.popdown()
            return
        if self._detail_history:
            page, adjustment, sort, letter, previous_detail, previous_title = self._detail_history.pop()
            if self._detail_page_name:
                detail = self.stack.get_child_by_name(self._detail_page_name)
                if detail:
                    self.stack.remove(detail)
                self._detail_scrolls.pop(self._detail_page_name, None)
                start = self._detail_indicator_starts.pop(self._detail_page_name, len(self._detail_indicators))
                del self._detail_indicators[start:]
                if self._detail_page_name in self._detail_page_names:
                    self._detail_page_names.remove(self._detail_page_name)
                self._detail_page_name = previous_detail
            self._active_page = page
            self.stack.set_visible_child_name(page)
            titles = {"listen": "Listen Now", "songs": "Songs", "albums": "Albums", "artists": "Artists", "settings": "Settings"}
            self.header_title.set_text(previous_title or titles.get(page, "Sonora"))
            if page in self._grid_sort:
                self._grid_sort[page] = sort
                self._grid_letter[page] = letter
            scroll = self._detail_scrolls.get(page) or {"listen": self.listen_page, "songs": self.songs_scroll,
                     "albums": self.albums_scroll, "artists": self.artists_scroll,
                     "favorites": self.favorites_page}.get(page)
            if scroll:
                GLib.idle_add(lambda: (scroll.get_vadjustment().set_value(adjustment), GLib.SOURCE_REMOVE)[1])
            self._update_back_button()
            return
        if self.split.get_collapsed() and self.split.get_show_content():
            self.split.set_show_content(False)

    def _collection_row(self, title, subtitle, tracks, icon="media-optical-symbolic"):
        row = Adw.ActionRow()
        row.set_use_markup(False)
        # Set tags after disabling markup: constructor-time title parsing would
        # otherwise treat '&' in artist or album names as an entity.
        row.set_title(title)
        row.set_subtitle(subtitle)
        row.add_prefix(self._cover_image(next((track.artwork_path for track in tracks if track.artwork_path), ""), 48, icon))
        play = Gtk.Button.new_from_icon_name("media-playback-start-symbolic")
        play.set_valign(Gtk.Align.CENTER)
        play.set_tooltip_text(f"Play {title}")
        play.connect("clicked", lambda *_: self.playback.play_track(tracks[0], tracks))
        row.add_suffix(play)
        return row

    def _refresh_folders(self):
        self._clear_list(self.folder_rows)
        for path in self.library.folders:
            row = Adw.ActionRow()
            row.set_use_markup(False)
            row.set_title(Path(path).name or path)
            row.set_subtitle(path)
            row.set_subtitle_lines(2)
            remove = Gtk.Button.new_from_icon_name("user-trash-symbolic")
            remove.set_tooltip_text("Remove folder from Sonora")
            remove.set_sensitive(not self.library.scanning)
            remove.set_valign(Gtk.Align.CENTER)
            remove.connect("clicked", lambda _button, folder=path: self._remove_folder(folder))
            row.add_suffix(remove)
            self.folder_rows.append(row)
        self.rescan_button.set_sensitive(bool(self.library.folders) and not self.library.scanning)
        self.cancel_button.set_visible(self.library.scanning)

    def _remove_folder(self, path):
        self.library.remove_folder(path)

    def _save_artist_exceptions(self, *_args):
        buffer = self.artist_exceptions.get_buffer()
        start, end = buffer.get_bounds()
        names = buffer.get_text(start, end, True).splitlines()
        self.library.database.set_artist_split_exceptions(names)
        self.exception_status.set_text("Saved. Artist groups are updated.")
        self._refresh()

    def _cover_image(self, path, size, icon="audio-x-generic-symbolic"):
        if path and Path(path).is_file():
            try:
                cache_key = (path, size)
                pixbuf = self._artwork_pixbufs.get(cache_key)
                if pixbuf is None:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, size, True)
                    self._artwork_pixbufs[cache_key] = pixbuf
                image = Gtk.Image.new_from_pixbuf(pixbuf)
                image.set_pixel_size(size)
                image.add_css_class("sonora-artwork-large" if size >= 100 else "sonora-artwork-small")
                image.set_overflow(Gtk.Overflow.HIDDEN)
                return image
            except GLib.Error:
                pass
        image = Gtk.Image.new_from_icon_name(icon)
        image.set_pixel_size(size)
        return image

    @staticmethod
    def _clear_list(widget):
        child = widget.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            widget.remove(child)
            child = next_child

    def _play_all(self, *_args):
        if self.library.tracks:
            self.playback.play_track(self.library.tracks[0], self.library.tracks)

    def _open_uri(self, uri: str) -> bool:
        try:
            file = Gio.File.new_for_uri(uri)
            path = file.get_path()
            if not path or Path(path).suffix.casefold() not in {".mp3", ".m4a"}:
                return False
            source = Path(path)
            if not source.is_file() or source.stat().st_size <= 0:
                return False
            existing = next((track for track in self.library.tracks if track.path == path), None)
            if existing:
                self.playback.play_track(existing, self.library.tracks)
                return True
            audio = MutagenFile(path, easy=True)
            if audio is None:
                return False
            tags = audio.tags or {}
            def first(*keys):
                for key in keys:
                    values = tags.get(key)
                    if values:
                        return str(values[0] if isinstance(values, (list, tuple)) else values)
                return ""
            track = Track(0, path, first("title") or Path(path).stem, first("artist"), first("albumartist"),
                          first("album"), first("genre"), 0, 0, 0,
                          int(audio.info.length * 1000) if audio.info and audio.info.length else 0, "", "")
            self.playback.play_track(track)
            return True
        except (OSError, ValueError, TypeError):
            return False

    def _sync_player(self):
        if not hasattr(self, "play_button"):
            return
        track = self.playback.current_track
        active = track is not None
        self.track_title_label.set_text(track.title if active else "Nothing playing")
        self.track_artist_label.set_text(self.playback.error or (track.display_artist if active else "Choose a song from your library"))
        artist_name = (track.primary_artist or track.display_artist) if active else ""
        self.track_artist.set_sensitive(active and bool(self._artist_tracks(artist_name)) and not self.playback.error)
        self.track_album_label.set_text(track.album if active and track.album else "")
        album_group = self._album_group_for_track(track)
        self.track_album.set_sensitive(bool(album_group))
        self.track_album.set_visible(bool(album_group))
        favorite = bool(active and track.id and self.library.database.is_favorite(track.id))
        self.current_favorite_button.set_active(favorite)
        self.current_favorite_button.set_sensitive(active and bool(track.id))
        self.current_favorite_button.set_label("♥" if favorite else "♡")
        self.current_favorite_button.set_tooltip_text("Remove from favorites" if favorite else "Add to favorites")
        for indicator in self._detail_indicators:
            selected = active and indicator.sonora_track_path == track.path
            indicator.set_text("♫" if selected else indicator.sonora_track_number)
            if selected:
                indicator.add_css_class("accent")
                indicator.remove_css_class("dim-label")
            else:
                indicator.remove_css_class("accent")
                indicator.add_css_class("dim-label")
        self.cover.set_from_paintable(self._cover_image(track.artwork_path, 48).get_paintable()) if active and track.artwork_path else self.cover.set_from_icon_name("audio-x-generic-symbolic")
        self.play_button.set_icon_name("media-playback-pause-symbolic" if self.playback.playing else "media-playback-start-symbolic")
        self.play_button.set_sensitive(active)
        self.prev_button.set_sensitive(active and self.playback.can_previous)
        self.next_button.set_sensitive(active and self.playback.can_next)
        self.seek_scale.set_sensitive(active and self.playback.duration_us > 0)
        self.duration_label.set_text(self._format_time(self.playback.duration_us // 1000))
        self._updating_volume = True
        self.volume_scale.set_value(self.playback.volume)
        self._updating_volume = False
        self._update_volume_icon(self.playback.volume)
        self.volume_button.set_active(self.playback.muted)
        self.shuffle_button.set_active(self.playback.shuffle_enabled)
        repeat_icon = "media-playlist-repeat-song-symbolic" if self.playback.loop_status == "Track" else "media-playlist-repeat-symbolic"
        self.repeat_button.set_icon_name(repeat_icon)
        repeat_name = {"None": "off", "Playlist": "all", "Track": "one"}[self.playback.loop_status]
        self.repeat_button.set_tooltip_text(f"Repeat {repeat_name} · click to change")
        self.queue_button.set_tooltip_text(f"Play queue · {len(self.playback.queue)} tracks")
        self._refresh_queue_popover()
        self._update_accent(track.artwork_accent if active else "")
        if self.mpris:
            self.mpris.emit_changed()
        self._persist_playback_state()

    def _open_now_playing(self):
        track = self.playback.current_track
        if track:
            self._open_detail("now-playing", track.title, [track])

    def _current_favorite_toggled(self, button):
        track = self.playback.current_track
        if track and track.id:
            self._toggle_favorite(track, button.get_active())

    def _open_current_artist(self):
        track = self.playback.current_track
        if track:
            name = track.primary_artist or track.display_artist
            self._open_artist(name, self._artist_tracks(name))

    def _open_track_context(self, track):
        if track.album:
            group = self._album_group_for_track(track)
            if group:
                self._open_album(*group)
                return
        name = track.primary_artist or track.display_artist
        artist_tracks = self._artist_tracks(name)
        if artist_tracks:
            self._open_artist(name, artist_tracks)
        else:
            self._play_specific(track, self.library.tracks)

    def _update_accent(self, accent):
        context = self.player_bar.get_style_context()
        if self._accent_provider:
            context.remove_provider(self._accent_provider)
            self._accent_provider = None
        if not accent or len(accent) != 7:
            return
        try:
            red, green, blue = (int(accent[index:index + 2], 16) for index in (1, 3, 5))
            self._accent_provider = Gtk.CssProvider()
            self._accent_provider.load_from_data(f"box {{ border-top: 2px solid rgba({red}, {green}, {blue}, 0.72); }}".encode())
            context.add_provider(self._accent_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        except (ValueError, GLib.Error):
            self._accent_provider = None

    def _seek_to(self, _scale, _scroll, value):
        if not self._updating_seek:
            self.playback.seek(int(value))
        return True

    def _volume_changed(self, scale):
        if not self._updating_volume:
            self.playback.set_volume(scale.get_value())
            self._update_volume_icon(scale.get_value())

    def _update_volume_icon(self, volume):
        icon = "audio-volume-muted-symbolic" if self.playback.muted or volume <= 0.01 else (
            "audio-volume-low-symbolic" if volume < 0.34 else (
                "audio-volume-medium-symbolic" if volume < 0.67 else "audio-volume-high-symbolic"))
        self.volume_button.set_child(Gtk.Image.new_from_icon_name(icon))

    def _tick(self):
        self.playback.record_progress()
        if not self.playback.current_track:
            return GLib.SOURCE_CONTINUE
        position_ms = self.playback.position_us // 1000
        duration_ms = self.playback.duration_us // 1000
        shown = max(0, duration_ms - position_ms) if self._show_remaining else position_ms
        self.position_label.set_text(("−" if self._show_remaining else "") + self._format_time(shown))
        self._updating_seek = True
        self.seek_scale.set_range(0, max(1, self.playback.duration_us // 1000))
        self.seek_scale.set_value(position_ms)
        self._updating_seek = False
        now = GLib.get_monotonic_time() / 1_000_000
        if now - self._last_persist >= 5:
            self._last_persist = now
            self._persist_playback_state()
        return GLib.SOURCE_CONTINUE

    @staticmethod
    def _format_time(milliseconds):
        seconds = max(0, int(milliseconds / 1000))
        return f"{seconds // 60}:{seconds % 60:02d}"

    def _close(self, *_args):
        GLib.source_remove(self._position_timer)
        self._persist_playback_state()
        self.library.cancel_scan()
        if self.mpris:
            self.mpris.close()
        self.playback.close()
        return False

    def _smoke_quit(self):
        self.get_application().quit()
        return GLib.SOURCE_REMOVE


def main():
    smoke = "--smoke-test" in sys.argv
    argv = [arg for arg in sys.argv if arg != "--smoke-test"]
    app = SonoraApplication(smoke_test=smoke)
    return app.run(argv)
