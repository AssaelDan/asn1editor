import argparse

import wx

import tests.TestPlugin
from asn1editor.wxPython.MainWindow import MainWindow

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='ASN.1 editor')
    parser.add_argument('-asn1spec', required=False, help='ASN.1 specification file name')
    parser.add_argument('-type', required=False, help='Name of the ASN.1 type to load (Module name.Type name)')
    parser.add_argument('-data', required=False, help='Data file to load')
    parser.add_argument('-test', required=False, help='Data file to load', action='store_true')

    args = parser.parse_args()

    app = wx.App()

    if args.test:
        frame = MainWindow([tests.TestPlugin.TestPlugin(), tests.TestPlugin.TestPlugin(" 2")])
    else:
        frame = MainWindow()
    if args.asn1spec is not None:
        app.ProcessPendingEvents()
        frame.load_spec(args.asn1spec, args.type)
    if args.data is not None:
        frame.load_data_from_file(args.data)

    frame.Show()

    app.MainLoop()
