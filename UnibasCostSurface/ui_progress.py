# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_progress.ui'
#
# Created: Sat Mar 23 14:24:38 2013
#      by: PyQt4 UI code generator 4.9.1
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_Progress(object):
    def setupUi(self, Progress):
        Progress.setObjectName(_fromUtf8("Progress"))
        Progress.resize(431, 111)
        self.gridLayout = QtGui.QGridLayout(Progress)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.buttonBox = QtGui.QDialogButtonBox(Progress)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout.addWidget(self.buttonBox, 4, 1, 1, 1)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem, 0, 0, 1, 1)
        self.lblProgress = QtGui.QLabel(Progress)
        self.lblProgress.setObjectName(_fromUtf8("lblProgress"))
        self.gridLayout.addWidget(self.lblProgress, 1, 0, 1, 1)
        self.progBar = QtGui.QProgressBar(Progress)
        self.progBar.setMaximum(0)
        self.progBar.setProperty("value", 0)
        self.progBar.setObjectName(_fromUtf8("progBar"))
        self.gridLayout.addWidget(self.progBar, 2, 0, 1, 2)
        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem1, 3, 1, 1, 1)

        self.retranslateUi(Progress)
        QtCore.QMetaObject.connectSlotsByName(Progress)

    def retranslateUi(self, Progress):
        Progress.setWindowTitle(QtGui.QApplication.translate("Progress", "Unibas Cost Surface Analysis Tool", None, QtGui.QApplication.UnicodeUTF8))
        self.lblProgress.setText(QtGui.QApplication.translate("Progress", "Progress...", None, QtGui.QApplication.UnicodeUTF8))

