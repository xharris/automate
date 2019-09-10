import sys
from PySide2 import QtCore, QtWidgets, QtGui

def main():
    app, widget = MainUI.start()
    sys.exit(app.exec_())

class MainUI(QtWidgets.QWidget):
    @staticmethod
    def start():
        app = QtWidgets.QApplication([])
        widget = MainUI();
        widget.resize(800, 600)
        widget.show()
        return app, widget

    def __init__(self):
        super().__init__()

        # box layouts
        self.box_main = QtWidgets.QHBoxLayout()
        self.box_left = QtWidgets.QVBoxLayout()
        self.box_right = QtWidgets.QVBoxLayout()

        # menubar (file: new, open, save, save as)
        # label: filename
        self.lbl_filename = QtWidgets.QLabel("myfile")
        self.box_left.addWidget(self.lbl_filename)
        # list: current file instructions
        # list: inspector
        # list: library

        self.box_main.addLayout(self.box_left,1)
        self.box_main.addLayout(self.box_right,1)
        self.setLayout(self.box_main)


if __name__ == "__main__":
    main()