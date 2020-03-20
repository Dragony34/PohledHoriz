# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PohledHoriz
                                 A QGIS plugin
 Shows view horizon from point on the map

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os
import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QLineEdit, QCompleter, QMessageBox, QProgressBar
from qgis.core import *
from qgis.gui import *
from osgeo import gdal
from .dialog import Dialog
from gdalconst import *
import numpy as np
import io


class PohledHoriz:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.vstupDialog = Dialog()

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        # Configure toolbar widget
        self.toolbar = self.iface.addToolBar("Shows view horizon from point")
        self.toolbar.setObjectName("Shows view horizon from point")

        self.find_btn = QAction(QIcon(os.path.join(os.path.dirname(__file__), "horizont.png")), "Show view horizon", self.iface.mainWindow())
        self.toolbar.addActions([self.find_btn])
        self.find_btn.triggered.connect(self.VymezeniOchrannehoPasma)

    def VymezeniOchrannehoPasma(self):
        # nacteni v stupu z dialogoveho okna
        self.vstupDialog.exec_()
        self.dmt = self.vstupDialog.mMapLayerComboBox.currentLayer().source()

        self.hrbetnice = self.vstupDialog.mMapLayerComboBox_2.currentLayer().source()
        velikostPasma = self.vstupDialog.lineEdit.text()

        ##Nacteni vstupnich rastru terenu a hrbetnic
        #self.setDialogcurrentIndex()
        raster_teren = self.dmt
        raster_hrbet = self.hrbetnice

        #QgsMessageLog.logMessage("vrstva " + str(self.dmt))                                           #dialogove okno, dodat maximalni ubytek vysek radek dialog. okna

        dataset = gdal.Open(str(self.dmt), GA_ReadOnly)                                              #otevre raster dataset pro cteni
        band = dataset.GetRasterBand(1)                                                             #cte specifickou vrstvu rastru


        self.sloupce = dataset.RasterXSize                                                           #velikost rastru v x-ove souradnici - pocet sloupcu
        self.radky = dataset.RasterYSize

        sloupce = dataset.RasterXSize  # velikost rastru v x-ove souradnici - pocet sloupcu
        radky = dataset.RasterYSize

        QgsMessageLog.logMessage("sloupcu:" + str(sloupce), 'PohledHoriz')#velikost rastru v y-ove souradnici - pocet radku
        QgsMessageLog.logMessage("radku:" + str(radky), 'PohledHoriz')

        rasterVysek = band.ReadAsArray()                                                            #cte primo matici rastru

        dataset = gdal.Open(str(self.hrbetnice), GA_ReadOnly)
        band = dataset.GetRasterBand(1)

        rasterHrbetnice = band.ReadAsArray()
        rasterAkumulace = band.ReadAsArray()

        rasterSnizeni = np.ones((radky, sloupce))

        #vytvoreni prazdneho dvourozmerneho pole rasterSnizeni o velikosti odpovidajici poctu radku a sloupcu vstupnimu rastru vysek
        rasterAkumulaceDalsi = np.ones((radky, sloupce))                                  #dtto
        rasterOchrannePasmo = np.ones((radky, sloupce))                                   #dtto

        minimalniHodnota = -9999

        ##Vypocet rastru / pole ubytku vysek

        for sloupec in range(1, sloupce - 1):                                                         #smycka projizdi vsechny sloupce rastru
            for radek in range(1, radky - 1):                                                     #smycka projizdi vsechny radky rastru
                Zpracovavana = rasterVysek[radek][sloupec]
                LevaHorni = rasterVysek[radek - 1][sloupec - 1]
                StredniHorni = rasterVysek[radek - 1][sloupec]
                PravavHorni = rasterVysek[radek + 1][sloupec + 1]
                LevaStredni = rasterVysek[radek][sloupec - 1]
                PravaStredni = rasterVysek[radek][sloupec + 1]
                LevaDolni = rasterVysek[radek + 1][sloupec - 1]
                StredniDolni = rasterVysek[radek + 1][sloupec]
                PravaDolni = rasterVysek[radek + 1][sloupec + 1]

                #QgsMessageLog.logMessage(str(LevaDolni), 'PohledHoriz')
                maximalniHodnota = max(LevaDolni, LevaHorni, LevaStredni, StredniDolni, StredniHorni, PravaDolni, PravaStredni, PravavHorni)             #nejvyssi snizeni = nejvetsi ubytek vysky
                rozdil = Zpracovavana - maximalniHodnota
                                                                            #spocitat z hodnot vyssich nez zpracovavana tu nejmensi (z vetsich nez zpracovavavana)
                if rozdil < 0:                                              #pokud bude rozdil zaporny
                    Snizeni = rozdil                                        #zapise se snizeni o kolik metru
                    #tu se bude pokracovat ve vypcotu
                else:
                    Snizeni = 0                                             #jinak bude snizeni nulove tzn nedojde ke zmene vysky
                rasterSnizeni[radek][sloupec] = Snizeni
        self.ulozeniDoAscii('c:/temp/snizeni.txt', rasterSnizeni)
                #QgsMessageLog.logMessage(str(rasterSnizeni), 'PohledHoriz')

        ##Vyplneni okrajovych pisloupecelu nulami
        for sloupec in range(0, sloupce):
            rasterSnizeni[0][sloupec] = 0                                                                   #horni prazdny radek okraj  (kdyztak prohodit znamenko)
            rasterSnizeni[radky - 1][sloupec] = 0                                                     #spodni prazdny radek okraj (kdyztak prehodit znamenko)
        for radek in range(0, radky):
            rasterSnizeni[radek][0] = 0                                                                  #levy prazdny sloupec okraj
            rasterSnizeni[radek][sloupce - 1] = 0                                                     #pravy prazdny sloupec okraj

        #for sloupec in range(0, sloupce):                             #loop iterating through columns of the raster
            #for radek in range(0, radky):                         #loop iterating through rows of the raster
                #rasterAkumulace[radek][sloupec] = rasterHrbetnice[radek][sloupec]       #prekopiruje se obsah hrbetnice do rastru akmulace, vychozi stav pro vypocet

        ##Akumulace ubytku vysek od hrbetnice
        def Akumulace():
            for sloupec in range(1, sloupce - 1):                             #loop iterating through columns of the raster
                for radek in range(1, radky - 1):
                    Zpracovavana = rasterAkumulace[radek][sloupec]
                    LevaHorni = rasterAkumulace[radek - 1][sloupec - 1]
                    StredniHorni = rasterAkumulace[radek - 1][sloupec]
                    PravavHorni = rasterAkumulace[radek + 1][sloupec + 1]
                    LevaStredni = rasterAkumulace[radek][sloupec - 1]
                    PravaStredni = rasterAkumulace[radek][sloupec + 1]
                    LevaDolni = rasterAkumulace[radek + 1][sloupec - 1]
                    StredniDolni = rasterAkumulace[radek + 1][sloupec]
                    PravaDolni = rasterAkumulace[radek + 1][sloupec + 1]

                    #pro vsechny bunky se zapisuje nova hodnota do rastrAkumulaceDalsi
                    if Zpracovavana == -9999:                                  #zjistuje jestli je bunka nevplynena akmuluaci tzn jestli je doposud prazdna
                        minAkumulaceZOkoli = max(LevaDolni, LevaHorni, LevaStredni, StredniDolni, StredniHorni, PravaDolni, PravaStredni, PravavHorni)  # maximalniHodnota je nejnizsi snizeni
                        if minAkumulaceZOkoli == -9999:                        #jestli je maximalni hodnota vsude okolo bunky NODATA VALUE, priradi hodnotu -999
                            rasterAkumulaceDalsi[radek][sloupec] = -9999
                        else:
                            rasterAkumulaceDalsi[radek][sloupec] = minAkumulaceZOkoli + rasterSnizeni[radek][sloupec]      #pokud ne, zapise se hodnota akumulace z okoli + ubytek vysek
                    else:
                        rasterAkumulaceDalsi[radek][sloupec] = rasterAkumulace[radek][sloupec]  #prepise se hodnota do rastrAkumulaceDalsi

            #prepise rastrAkumulace jako vstupni rastr pro dalsi cyklus sireni a soucasne hleda minimalni hodnotu aby tento cyklus mel vubec smysl poustet
            minimalniHodnota = int(-9999)
            opakovat = False
            for sloupec in range(1, sloupce - 1):
                for radek in range(1, radky - 1):
                    rasterAkumulace[radek][sloupec] = rasterAkumulaceDalsi[radek][sloupec]
                    if rasterAkumulaceDalsi[radek][sloupec] == minimalniHodnota:   #jestli se v celem rastru akumulace vyskytuje alespon jedna nevyplnena bunka
                        opakovat = True
            if opakovat:                                                 #pokud jsou v rastru bunky s hodnotou -999, spusti se Akumulace()
                Akumulace()
                self.ulozeniDoAscii('c:/temp/akumulace.txt', rasterAkumulaceDalsi)

        Akumulace()

        ##Vymezeni ochranneho pasma
        ochranne_pasmo = int(velikostPasma)
        for sloupec in range(0, sloupce):
            for radek in range(0, radky):
                if abs(rasterAkumulaceDalsi[radek][sloupec]) < int(ochranne_pasmo): #pokud je velikost ochranneho pasma vetsi nez akumulace ubytku vysek
                    rasterOchrannePasmo[radek][sloupec] = 1 #-> chraneno
                    proVystup = 1
                else:
                    rasterOchrannePasmo[radek][sloupec] = 0 #jinak -> nechraneno
                    proVystup = 0
        self.ulozeniDoAscii('c:/temp/ochr_pasmo.txt', rasterOchrannePasmo)

    def ulozeniDoAscii(self, soubor, pole):
        soubor = open(soubor,'w')
        soubor.write("ncols         51" + '\n')
        soubor.write("nrows         36" + '\n')
        soubor.write("xllcorner     -475650.97663479" + '\n')
        soubor.write("yllcorner     -1134520.3457931" + '\n')
        soubor.write("cellsize      200" + '\n')
        soubor.write("NODATA_value  -9999" + '\n')
        for sloupec in range(0, self.sloupce):
            for radek in range(0, self.radky):
                soubor.write(str(pole[radek][sloupec]) + " ")
            soubor.write('\n')
        soubor.close()


    def unload(self):
        """Removes the icon (toolbar) from QGIS GUI."""
        # remove the toolbar
        del self.toolbar