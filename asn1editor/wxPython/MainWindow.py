import sys
import typing
from typing import Optional

import wx
import wx.svg

import asn1editor
import asn1editor.wxPython.Settings as Settings
from asn1editor import Plugin
from asn1editor.ASN1SpecHandler import ASN1SpecHandler
from asn1editor.PluginInterface import PluginInterface
from asn1editor.wxPython import WxPythonViewFactory
from asn1editor.wxPython.FilePickerHandler import FilePickerHandler
from asn1editor.wxPython.Resources import resource_path


class MainWindow(wx.Frame, PluginInterface):
    def __init__(self, plugin: Optional[Plugin] = None):
        super(MainWindow, self).__init__(None, title='ASN.1 editor ' + asn1editor.__version__, size=(500, 800))

        self.__plugin = plugin
        if self.__plugin is not None:
            self.__plugin.connect(self)

        Settings.load()

        self.SetSize(wx.Size(Settings.settings.get('size', (500, 800))))
        self.Maximize(Settings.settings.get('maximized', True))
        self.SetPosition(wx.Point(Settings.settings.get('position', (0, 0))))

        self.__main_panel = wx.ScrolledWindow(self, style=wx.HSCROLL | wx.VSCROLL)
        self.__main_panel.SetScrollbars(15, 15, 50, 50)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.__main_panel.SetSizer(sizer)
        self.__main_panel.SetAutoLayout(True)

        self._status_bar = self.CreateStatusBar()

        self.__create_menu()
        self.__asn1_handler = None

        self.__model = None
        self.__view = None
        self.__controller = None
        self.__type_name = None
        self.__file_name = None

        self.bind_events()

        # noinspection SpellCheckingInspection
        sys.excepthook = self.__exception_handler

    def __create_menu(self):
        menu_bar = wx.MenuBar()
        file_menu = wx.Menu()
        self.__load_spec_item: wx.MenuItem = file_menu.Append(wx.ID_ANY, 'Open ASN.1 specification')
        # noinspection PyArgumentList
        image: wx.svg.SVGimage = wx.svg.SVGimage.CreateFromFile(resource_path('icons/open.svg'))
        self.__load_spec_item.SetBitmap(image.ConvertToBitmap(width=16, height=16))
        file_menu.AppendSeparator()
        self.__load_data_item: wx.MenuItem = file_menu.Append(wx.ID_OPEN, 'Load encoded data')
        # noinspection PyArgumentList
        image: wx.svg.SVGimage = wx.svg.SVGimage.CreateFromFile(resource_path('icons/load_encoded.svg'))
        self.__load_data_item.SetBitmap(image.ConvertToBitmap(width=16, height=16))
        self.__load_data_item.Enable(False)
        self.__save_data_item: wx.MenuItem = file_menu.Append(wx.ID_SAVE, 'Save encoded data')
        # noinspection PyArgumentList
        image: wx.svg.SVGimage = wx.svg.SVGimage.CreateFromFile(resource_path('icons/save_encoded.svg'))
        self.__save_data_item.SetBitmap(image.ConvertToBitmap(width=16, height=16))
        self.__save_data_item.Enable(False)
        file_menu.AppendSeparator()
        self.__exit_item = file_menu.Append(wx.ID_EXIT, 'Exit', 'Exit application')
        # noinspection PyArgumentList
        image: wx.svg.SVGimage = wx.svg.SVGimage.CreateFromFile(resource_path('icons/exit.svg'))
        self.__exit_item.SetBitmap(image.ConvertToBitmap(width=16, height=16))
        menu_bar.Append(file_menu, '&File')

        if self.__plugin is not None:
            plugin_menu = wx.Menu()
            menus = self.__plugin.get_menus()
            for i, menu in enumerate(menus):
                if not len(menu[0]):
                    plugin_menu.AppendSeparator()
                else:
                    menu_item: wx.MenuItem = plugin_menu.Append(i, menu[0])
                    if menu[1] is not None:
                        self.Bind(wx.EVT_MENU, self.__plugin_menu_event, menu_item)
                    else:
                        menu_item.Enable(False)

            menu_bar.Append(plugin_menu, self.__plugin.get_name())

        help_menu = wx.Menu()
        about_item = help_menu.Append(wx.ID_ABOUT, 'About')
        self.Bind(wx.EVT_MENU, self.__about_item_event, about_item)
        menu_bar.Append(help_menu, '&Help')

        self.SetMenuBar(menu_bar)

    def __plugin_menu_event(self, e):
        self.__plugin.get_menus()[e.GetId()][1]()

    def bind_events(self):
        def schema_dialog_constructor() -> wx.FileDialog:
            return wx.FileDialog(self, "ASN.1 schema", wildcard="ASN.1 files (*.asn)|*.asn",
                                 style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE)

        def data_load_dialog_constructor() -> wx.FileDialog:
            extensions = ';'.join(ASN1SpecHandler.get_extensions())
            return wx.FileDialog(self, "ASN.1 encoded file", wildcard=f"ASN.1 encoded ({extensions})|{extensions}",
                                 style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

        def data_save_dialog_constructor() -> wx.FileDialog:
            extensions = ';'.join(ASN1SpecHandler.get_extensions())
            return wx.FileDialog(self, "ASN.1 encoded file", wildcard=f"ASN.1 encoded ({extensions})|{extensions}", style=wx.FD_SAVE)

        self.Bind(wx.EVT_MENU, self.exit, self.__exit_item)

        picker = FilePickerHandler(schema_dialog_constructor, self.load_spec)
        self.Bind(wx.EVT_MENU, picker.on_menu_click, self.__load_spec_item)

        picker = FilePickerHandler(data_load_dialog_constructor, self.load_data_from_file)
        self.Bind(wx.EVT_MENU, picker.on_menu_click, self.__load_data_item)

        picker = FilePickerHandler(data_save_dialog_constructor, self.save_data_to_file, True)
        self.Bind(wx.EVT_MENU, picker.on_menu_click, self.__save_data_item)

        self.Bind(wx.EVT_CLOSE, self.close, self)

    def load_spec(self, file_name: str, type_name: Optional[str] = None):
        # Spec file loaded, compile it to show a selection of type names
        if not self.__asn1_handler or file_name not in self.__asn1_handler.get_filename():
            self.__asn1_handler = ASN1SpecHandler(file_name)

        if type_name is None:
            types = self.__asn1_handler.get_types()
            dialog = wx.SingleChoiceDialog(self, 'Select type from ASN.1 file', 'Select type', types)
            try:
                if dialog.ShowModal() == wx.ID_OK:
                    self.__type_name = dialog.GetStringSelection()
            finally:
                dialog.Destroy()
        else:
            self.__type_name = type_name
        if self.__type_name is not None:
            self._status_bar.SetStatusText(f'Loaded {file_name}')
            self.__file_name = file_name

            view_factory = WxPythonViewFactory.WxPythonViewFactory(self.__main_panel)
            view_factory.freeze()

            if self.__view is not None:
                self.__view.destroy()

            self.__view, self.__controller = self.__asn1_handler.create_mvc_for_type(self.__type_name, view_factory)
            sizer: wx.Sizer = self.__main_panel.GetSizer()
            sizer.Clear()
            sizer.Add(self.__view.realize(), 0, wx.ALL | wx.EXPAND, 5)
            sizer.Layout()

            self.__main_panel.SetSizer(sizer)
            self.__main_panel.FitInside()
            self.__main_panel.AdjustScrollbars()

            view_factory.thaw()

            self.__load_data_item.Enable(True)
            self.__save_data_item.Enable(True)

    def load_data_from_file(self, file_name: str):
        self.__controller.model_to_view(self.__asn1_handler.load_data_file(file_name))
        self._status_bar.SetStatusText(f'Loaded {file_name} for {self.__type_name}')

    def save_data_to_file(self, file_name: str):
        self.__asn1_handler.save_data_file(file_name, self.__controller.view_to_model())

    def show_data(self, data: bytes, codec: str):
        self.__controller.model_to_view(self.__asn1_handler.get_model_from_data(data, codec))
        self._status_bar.SetStatusText(f'Loaded data for {self.__type_name}')

    def file_picker(self, message: str, wildcard: str, open_: bool) -> typing.Optional[str]:
        def dialog_constructor() -> wx.FileDialog:
            return wx.FileDialog(self, message, wildcard=wildcard,
                                 style=(wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) if open_ else wx.FD_SAVE)

        picker = FilePickerHandler(dialog_constructor, None, not open_)
        picker.on_menu_click(wx.EVT_MENU)
        return picker.filename

    def dir_picker(self, message: str) -> typing.Optional[str]:
        def dialog_constructor() -> wx.DirDialog:
            return wx.DirDialog(self, message,
                                style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)

        picker = FilePickerHandler(dialog_constructor, None)
        picker.on_menu_click(wx.EVT_MENU)
        return picker.filename

    def encode_data(self, codec: str) -> bytes:
        return self.__asn1_handler.get_data_from_model(self.__controller.view_to_model(), codec)

    def get_spec_filename(self) -> str:
        return self.__file_name

    def get_typename(self) -> str:
        return self.__type_name

    def get_spec(self, codec: str):
        return self.__asn1_handler.get_compiled(codec)

    def text_entry(self, message: str) -> typing.Optional[str]:
        with wx.TextEntryDialog(self, message) as text_dialog:
            if text_dialog.ShowModal() == wx.ID_CANCEL:
                return
            return text_dialog.GetValue()

    def choice_entry(self, message: str, choices: typing.List[str]) -> typing.Optional[str]:
        with wx.SingleChoiceDialog(self, message, '', choices=choices) as choice_dialog:
            if choice_dialog.ShowModal() == wx.ID_CANCEL:
                return
            return choice_dialog.GetStringSelection()

    def show_status(self, message: str):
        self._status_bar.SetStatusText(message)

    def __exception_handler(self, exc_type, value, trace):
        import traceback
        trace = ''.join(traceback.format_exception(exc_type, value, trace))
        print(trace)

        message = f'{value}\n\n{str(exc_type)}'
        exception_str = f'{message}\n\n{trace}'
        wx.MessageBox(message, 'Error', wx.OK | wx.ICON_ERROR, parent=self)
        self._status_bar.SetStatusText(f'Error: {value}')
        try:
            with open('error_log.txt', 'a+') as f:
                import datetime
                f.write(f'{datetime.datetime.now()}: {exception_str}\n\n')
        finally:
            pass

    # noinspection PyUnusedLocal
    def __about_item_event(self, e):
        del e
        dialog = wx.MessageDialog(self, f'''asn1editor {asn1editor.__version__}

Florian Fetz, 2020
https://github.com/Futsch1/asn1editor
''', style=wx.ICON_INFORMATION | wx.OK, caption='About')
        dialog.ShowModal()

    # noinspection PyUnusedLocal
    def exit(self, e: wx.Event):
        del e
        self.Close()

    # noinspection PyUnusedLocal
    def close(self, e: wx.Event):
        Settings.settings['size'] = (self.GetSize().Get())
        Settings.settings['maximized'] = self.IsMaximized()
        Settings.settings['position'] = self.GetPosition().Get()

        Settings.save()

        self.Destroy()
