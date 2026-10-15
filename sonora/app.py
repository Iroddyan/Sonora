from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Adw, Gio, GLib, Gtk, GdkPixbuf
from mutagen import File as MutagenFile

from sonora.library import LibraryService
from sonora.models import Track
from sonora.mpris import MprisService
from sonora.playback import PlaybackService


APP_ID = "io.github.Iroddyan.Sonora"


class SonoraApplication(Adw.Application):
    def __init__(self, smoke_test=False):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
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
        self.library = LibraryService(self._refresh, self._scan_progress_changed)
        self.playback = PlaybackService(
            self._sync_player,
            on_session_started=self.library.database.start_playback,
            on_listened=self.library.database.add_listened_time,
            on_session_ended=self.library.database.finish_playback,
        )
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

        self.nav_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.nav_list.add_css_class("navigation-sidebar")
        self.nav_list.set_margin_start(8)
        self.nav_list.set_margin_end(8)
        self.nav_list.set_margin_top(8)
        self.nav_list.set_vexpand(True)
        self.nav_list.connect("row-selected", self._on_nav_selected)
        sidebar.append(self.nav_list)
        for key, title, icon in (
            ("listen", "Listen Now", "audio-x-generic-symbolic"),
            ("songs", "Songs", "view-list-symbolic"),
            ("albums", "Albums", "media-optical-symbolic"),
            ("artists", "Artists", "avatar-default-symbolic"),
        ):
            row = Adw.ActionRow(title=title)
            row.set_activatable(True)
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
            row.sonora_page = key
            self.nav_list.append(row)
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
        self.back_button.set_tooltip_text("Back to navigation")
        self.back_button.set_visible(False)
        self.back_button.connect("clicked", lambda *_: self.split.set_show_content(False))
        self.header.pack_start(self.back_button)
        self.split.connect("notify::collapsed", self._update_back_button)
        self.split.connect("notify::show-content", self._update_back_button)
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search your music")
        self.search_entry.set_width_chars(22)
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.header.pack_end(self.search_entry)
        self.add_button = Gtk.Button(label="Add folder")
        self.add_button.add_css_class("suggested-action")
        self.add_button.connect("clicked", self._choose_folder)
        self.header.pack_end(self.add_button)
        self.content_toolbar.add_top_bar(self.header)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=160)
        self.stack.set_vexpand(True)
        self._build_listen_page()
        self._build_songs_page()
        self._build_albums_page()
        self._build_artists_page()
        self._build_settings_page()
        self.content_toolbar.set_content(self.stack)
        self._build_player()
        compact_player = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 760sp"))
        compact_player.add_setter(self.position_label, "visible", False)
        compact_player.add_setter(self.duration_label, "visible", False)
        compact_player.add_setter(self.player_details, "width-request", 132)
        self.add_breakpoint(compact_player)
        self.content_toolbar.add_bottom_bar(self.player_bar)

        self.content_page = Adw.NavigationPage(child=self.content_toolbar, title="Sonora")
        self.split.set_sidebar(self.sidebar_page)
        self.split.set_content(self.content_page)
        self.set_content(self.split)
        self.nav_list.select_row(self.nav_list.get_row_at_index(0))

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
        self.home_title = Gtk.Label(label="Listen now", xalign=0, css_classes=["title-1"])
        self.home_description = Gtk.Label(label="Your music, in one place.", xalign=0)
        self.home_description.add_css_class("dim-label")
        self.home_library_status = Gtk.Label(xalign=0)
        self.home_library_status.add_css_class("dim-label")
        hero_labels.append(self.home_title)
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
        self.home_recent = self._home_section("Recently added", "songs")
        self.home_artists = self._home_section("Artists in your library", "artists")
        self.home_songs = self._home_section("Songs in your library", "songs", vertical=True)
        self.home_albums = self._home_section("Albums in your library", "albums")
        for section in (self.home_recent, self.home_artists, self.home_songs, self.home_albums):
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
        scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.songs_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.songs_list.add_css_class("boxed-list")
        self.songs_list.set_placeholder(Gtk.Label(label="No songs match your search."))
        self.songs_list.connect("row-activated", self._activate_track_row)
        scroll.set_child(self.songs_list)
        box.append(scroll)
        self.stack.add_named(box, "songs")

    def _build_albums_page(self):
        box = self._page_list()
        self.albums_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.albums_list.add_css_class("boxed-list")
        self.albums_list.set_placeholder(Adw.StatusPage(icon_name="media-optical-symbolic", title="No albums yet", description="Album groups appear after Sonora indexes music with album tags."))
        scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER, child=self.albums_list)
        box.append(scroll)
        self.stack.add_named(box, "albums")

    def _build_artists_page(self):
        box = self._page_list()
        self.artists_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.artists_list.add_css_class("boxed-list")
        self.artists_list.set_placeholder(Adw.StatusPage(icon_name="avatar-default-symbolic", title="No artists yet", description="Artists appear after Sonora indexes your local music."))
        scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER, child=self.artists_list)
        box.append(scroll)
        self.stack.add_named(box, "artists")

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
        self.stack.add_named(Adw.Clamp(child=page, maximum_size=760), "settings")

    def _build_player(self):
        self.player_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.player_bar.set_margin_start(16)
        self.player_bar.set_margin_end(16)
        self.player_bar.set_margin_top(8)
        self.player_bar.set_margin_bottom(8)
        self.player_bar.add_css_class("sonora-player")
        self.cover = Gtk.Image.new_from_icon_name("audio-x-generic-symbolic")
        self.cover.set_pixel_size(44)
        self.cover.set_size_request(48, 48)
        self.player_bar.append(self.cover)
        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        details.set_size_request(180, -1)
        self.player_details = details
        self.track_title = Gtk.Label(label="Nothing playing", xalign=0, ellipsize=3)
        self.track_title.add_css_class("heading")
        self.track_artist = Gtk.Label(label="Add a folder or choose a song", xalign=0, ellipsize=3)
        self.track_artist.add_css_class("dim-label")
        details.append(self.track_title)
        details.append(self.track_artist)
        self.player_bar.append(details)

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

        self.position_label = Gtk.Label(label="0:00", css_classes=["numeric"])
        self.player_bar.append(self.position_label)
        self.seek_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 1000)
        self.seek_scale.set_draw_value(False)
        self.seek_scale.set_hexpand(True)
        self.seek_scale.set_size_request(110, -1)
        self.seek_scale.connect("change-value", self._seek_to)
        self.player_bar.append(self.seek_scale)
        self.duration_label = Gtk.Label(label="0:00", css_classes=["numeric", "dim-label"])
        self.player_bar.append(self.duration_label)

        volume_button = Gtk.MenuButton()
        volume_button.set_icon_name("audio-volume-high-symbolic")
        volume_button.set_tooltip_text("Volume")
        volume_popover = Gtk.Popover()
        volume_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        volume_box.set_margin_start(14)
        volume_box.set_margin_end(14)
        volume_box.set_margin_top(12)
        volume_box.set_margin_bottom(12)
        volume_box.append(Gtk.Image.new_from_icon_name("audio-volume-high-symbolic"))
        self.volume_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 0.05)
        self.volume_scale.set_draw_value(False)
        self.volume_scale.set_value(self.playback.volume)
        self.volume_scale.set_size_request(150, -1)
        self.volume_scale.connect("value-changed", self._volume_changed)
        volume_box.append(self.volume_scale)
        volume_popover.set_child(volume_box)
        volume_button.set_popover(volume_popover)
        self.player_bar.append(volume_button)

    def _on_nav_selected(self, _list, row):
        if row is None or not getattr(row, "sonora_page", None):
            return
        if _list is self.settings_list:
            self.nav_list.unselect_all()
        else:
            self.settings_list.unselect_all()
        self._show_page(row.sonora_page)

    def _update_back_button(self, *_args):
        if hasattr(self, "back_button"):
            self.back_button.set_visible(self.split.get_collapsed() and self.split.get_show_content())

    def _show_page(self, page: str):
        self._active_page = page
        titles = {"listen": "Listen Now", "songs": "Songs", "albums": "Albums", "artists": "Artists", "settings": "Settings"}
        self.header_title.set_text(titles.get(page, "Sonora"))
        self.stack.set_visible_child_name(page)
        self.add_button.set_visible(page != "settings")
        self.search_entry.set_visible(page != "settings")
        if page == "listen" and self.split.get_collapsed():
            self.split.set_show_content(True)
        if page != "listen" and self.split.get_collapsed():
            self.split.set_show_content(True)

    def _on_search_changed(self, entry):
        if entry.get_text().strip() and self._active_page not in {"songs", "settings"}:
            self.nav_list.select_row(self.nav_list.get_row_at_index(1))
        self._refresh_songs()

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
            self.playback.play_track(track, self.library.tracks)

    def _play_specific(self, track, queue):
        self.playback.play_track(track, queue)

    def _refresh(self):
        if not hasattr(self, "stack"):
            return
        self._refresh_listen()
        self._refresh_songs()
        self._refresh_collections()
        self._refresh_folders()
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
            return

        for section in (self.home_recent, self.home_artists, self.home_songs, self.home_albums):
            self._clear_list(section["content"])

        recently_added = sorted(tracks, key=lambda track: track.title.casefold())
        recently_added.sort(key=lambda track: track.first_added_at or "", reverse=True)
        recently_added = recently_added[:10]
        for track in recently_added:
            self.home_recent["content"].append(self._home_track_card(track))

        artists: dict[str, list[Track]] = defaultdict(list)
        for track in tracks:
            artist = track.artist or track.album_artist
            if artist:
                artists[artist].append(track)
        top_library_artists = sorted(artists.items(), key=lambda item: (-len(item[1]), item[0].casefold()))[:10]
        if top_library_artists:
            for artist, artist_tracks in top_library_artists:
                count_label = "song" if len(artist_tracks) == 1 else "songs"
                self.home_artists["content"].append(self._home_collection_card(
                    artist, f"{len(artist_tracks)} {count_label}", artist_tracks, "avatar-default-symbolic"))
        else:
            self._home_empty_label(self.home_artists["content"], "No artist tags found in this library yet.")

        for track in recently_added[:6]:
            self.home_songs["content"].append(self._home_song_row(track))

        albums: dict[tuple[str, str], list[Track]] = defaultdict(list)
        for track in tracks:
            if track.album:
                albums[(track.album_artist or track.artist or "Unknown artist", track.album)].append(track)
        album_groups = sorted(albums.items(), key=lambda item: (item[0][1].casefold(), item[0][0].casefold()))[:10]
        if album_groups:
            for (artist, album), album_tracks in album_groups:
                ordered_tracks = sorted(album_tracks, key=lambda track: (track.disc_number or 1,
                                                                          track.track_number or 10_000,
                                                                          track.title.casefold()))
                self.home_albums["content"].append(self._home_collection_card(
                    album, artist, ordered_tracks, "media-optical-symbolic"))
        else:
            self._home_empty_label(self.home_albums["content"], "No album tags found in this library yet.")

    def _home_track_card(self, track):
        button = Gtk.Button()
        button.add_css_class("card")
        button.add_css_class("flat")
        button.set_size_request(152, 210)
        button.set_tooltip_text(f"Play {track.title}")
        button.connect("clicked", lambda *_: self._play_specific(track, self.library.tracks))
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.set_margin_start(8)
        card.set_margin_end(8)
        card.set_margin_top(8)
        card.set_margin_bottom(8)
        card.append(self._cover_image(track.artwork_path, 132))
        title = Gtk.Label(label=track.title, xalign=0, ellipsize=3, max_width_chars=18)
        title.add_css_class("heading")
        artist = Gtk.Label(label=track.display_artist, xalign=0, ellipsize=3, max_width_chars=18)
        artist.add_css_class("dim-label")
        card.append(title)
        card.append(artist)
        button.set_child(card)
        return button

    def _home_collection_card(self, title, subtitle, tracks, icon):
        button = Gtk.Button()
        button.add_css_class("card")
        button.add_css_class("flat")
        button.set_size_request(152, 210)
        button.set_tooltip_text(f"Play {title}")
        button.connect("clicked", lambda *_: self.playback.play_track(tracks[0], tracks))
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.set_margin_start(8)
        card.set_margin_end(8)
        card.set_margin_top(8)
        card.set_margin_bottom(8)
        artwork = next((track.artwork_path for track in tracks if track.artwork_path), "")
        card.append(self._cover_image(artwork, 132, icon))
        title_label = Gtk.Label(label=title, xalign=0, ellipsize=3, max_width_chars=18)
        title_label.add_css_class("heading")
        subtitle_label = Gtk.Label(label=subtitle, xalign=0, ellipsize=3, max_width_chars=18)
        subtitle_label.add_css_class("dim-label")
        card.append(title_label)
        card.append(subtitle_label)
        button.set_child(card)
        return button

    def _home_song_row(self, track):
        row = Adw.ActionRow()
        row.set_use_markup(False)
        row.set_title(track.title)
        row.set_subtitle(" · ".join(part for part in (track.display_artist, track.album) if part))
        row.add_prefix(self._cover_image(track.artwork_path, 40))
        play = Gtk.Button.new_from_icon_name("media-playback-start-symbolic")
        play.set_tooltip_text(f"Play {track.title}")
        play.set_valign(Gtk.Align.CENTER)
        play.connect("clicked", lambda *_: self._play_specific(track, self.library.tracks))
        row.add_suffix(play)
        return row

    @staticmethod
    def _home_empty_label(container, text):
        label = Gtk.Label(label=text, xalign=0)
        label.add_css_class("dim-label")
        label.set_margin_top(8)
        label.set_margin_bottom(8)
        container.append(label)

    def _navigate_to(self, page):
        row_index = {"songs": 1, "albums": 2, "artists": 3}.get(page)
        if row_index is not None:
            self.nav_list.select_row(self.nav_list.get_row_at_index(row_index))

    def _refresh_songs(self):
        if not hasattr(self, "songs_list"):
            return
        self._clear_list(self.songs_list)
        tracks = self.library.search(self.search_entry.get_text()) if hasattr(self, "search_entry") else self.library.tracks
        for track in tracks:
            row = self._track_row(track)
            self.songs_list.append(row)
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

    def _track_row(self, track):
        row = Gtk.ListBoxRow()
        row.set_activatable(True)
        # PyGObject 3.56+ intentionally disables GObject's legacy data API.
        row.sonora_track = track
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        cover = self._cover_image(track.artwork_path, 40)
        box.append(cover)
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        labels.set_hexpand(True)
        title = Gtk.Label(label=track.title, xalign=0, ellipsize=3)
        title.add_css_class("heading")
        subtitle = " · ".join(part for part in (track.display_artist, track.album) if part)
        detail = Gtk.Label(label=subtitle, xalign=0, ellipsize=3)
        detail.add_css_class("dim-label")
        labels.append(title)
        labels.append(detail)
        box.append(labels)
        duration = Gtk.Label(label=self._format_time(track.duration_ms))
        duration.add_css_class("numeric")
        duration.add_css_class("dim-label")
        box.append(duration)
        play = Gtk.Button.new_from_icon_name("media-playback-start-symbolic")
        play.set_tooltip_text(f"Play {track.title}")
        play.connect("clicked", lambda *_: self._play_specific(track, tracks_for_row))
        tracks_for_row = self.library.tracks
        box.append(play)
        row.set_child(box)
        return row

    def _refresh_collections(self):
        self._clear_list(self.albums_list)
        self._clear_list(self.artists_list)
        albums: dict[tuple[str, str], list] = defaultdict(list)
        artists: dict[str, list] = defaultdict(list)
        for track in self.library.tracks:
            albums[(track.album_artist or track.artist or "Unknown artist", track.album or "Unknown album")].append(track)
            artists[track.artist or track.album_artist or "Unknown artist"].append(track)
        for (artist, album), tracks in sorted(albums.items(), key=lambda item: (item[0][1].casefold(), item[0][0].casefold())):
            row = self._collection_row(album, artist, tracks)
            self.albums_list.append(row)
        for artist, tracks in sorted(artists.items(), key=lambda item: item[0].casefold()):
            albums_count = len({track.album for track in tracks if track.album})
            row = self._collection_row(artist, f"{albums_count} albums · {len(tracks)} songs", tracks, icon="avatar-default-symbolic")
            self.artists_list.append(row)

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

    def _cover_image(self, path, size, icon="audio-x-generic-symbolic"):
        if path and Path(path).is_file():
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, size, True)
                image = Gtk.Image.new_from_pixbuf(pixbuf)
                image.set_pixel_size(size)
                image.add_css_class("sonora-cover")
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
        self.track_title.set_text(track.title if active else "Nothing playing")
        self.track_artist.set_text(self.playback.error or (track.display_artist if active else "Choose a song from your library"))
        self.cover.set_from_paintable(self._cover_image(track.artwork_path, 48).get_paintable()) if active and track.artwork_path else self.cover.set_from_icon_name("audio-x-generic-symbolic")
        self.play_button.set_icon_name("media-playback-pause-symbolic" if self.playback.playing else "media-playback-start-symbolic")
        self.play_button.set_sensitive(active)
        self.prev_button.set_sensitive(active and (self.playback.index > 0 or self.playback.position_us > 3_000_000))
        self.next_button.set_sensitive(active and self.playback.index + 1 < len(self.playback.queue))
        self.seek_scale.set_sensitive(active and self.playback.duration_us > 0)
        self.duration_label.set_text(self._format_time(self.playback.duration_us // 1000))
        self._update_accent(track.artwork_accent if active else "")
        if self.mpris:
            self.mpris.emit_changed()

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

    def _tick(self):
        self.playback.record_progress()
        if not self.playback.current_track:
            return GLib.SOURCE_CONTINUE
        position_ms = self.playback.position_us // 1000
        self.position_label.set_text(self._format_time(position_ms))
        self._updating_seek = True
        self.seek_scale.set_range(0, max(1, self.playback.duration_us // 1000))
        self.seek_scale.set_value(position_ms)
        self._updating_seek = False
        return GLib.SOURCE_CONTINUE

    @staticmethod
    def _format_time(milliseconds):
        seconds = max(0, int(milliseconds / 1000))
        return f"{seconds // 60}:{seconds % 60:02d}"

    def _close(self, *_args):
        GLib.source_remove(self._position_timer)
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
