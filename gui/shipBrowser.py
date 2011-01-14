import wx
import copy
from gui import bitmapLoader
import gui.mainFrame
import gui.globalEvents as GE
import time
from gui.PFListPane import PFListPane
import service

from wx.lib.buttons import GenBitmapButton

import gui.utils.colorUtils as colorUtils
import gui.utils.drawUtils as drawUtils

FitRenamed, EVT_FIT_RENAMED = wx.lib.newevent.NewEvent()
FitSelected, EVT_FIT_SELECTED = wx.lib.newevent.NewEvent()
FitRemoved, EVT_FIT_REMOVED = wx.lib.newevent.NewEvent()

Stage1Selected, EVT_SB_STAGE1_SEL = wx.lib.newevent.NewEvent()
Stage2Selected, EVT_SB_STAGE2_SEL = wx.lib.newevent.NewEvent()
Stage3Selected, EVT_SB_STAGE3_SEL = wx.lib.newevent.NewEvent()
SearchSelected, EVT_SB_SEARCH_SEL = wx.lib.newevent.NewEvent()

SB_ITEM_NORMAL = 0
SB_ITEM_SELECTED = 1
SB_ITEM_HIGHLIGHTED = 2
SB_ITEM_DISABLED = 4

BTN_NORMAL   = 1
BTN_PRESSED  = 2
BTN_HOVER    = 4
BTN_DISABLED = 8

class PFWidgetsContainer(PFListPane):
    def __init__(self,parent):
        PFListPane.__init__(self,parent)

    def IsWidgetSelectedByContext(self, widget):
        mainFrame = gui.mainFrame.MainFrame.getInstance()
        stage = self.Parent.GetActiveStage()
        fit = mainFrame.getActiveFit()
        if stage == 3 or stage == 4:
            if self._wList[widget].GetType() == 3:
                if fit == self._wList[widget].fitID:
                    return True
        return False


class ShipBrowser(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__ (self, parent,style = 0)

        self._lastWidth = 0
        self._activeStage = 1
        self._lastStage = 0
        self.browseHist = []
        self.lastStage = (0,0)
        self.mainFrame = gui.mainFrame.MainFrame.getInstance()

        self.categoryList=[]

        self._stage1Data = -1
        self._stage2Data = -1
        self._stage3Data = -1
        self._stage3ShipName = ""
        self.fitIDMustEditName = -1
        self.filterShipsWithNoFits = False

        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)

        mainSizer = wx.BoxSizer(wx.VERTICAL)

        self.hpane = HeaderPane(self)
        mainSizer.Add(self.hpane, 0, wx.EXPAND)

        self.m_sl2 = wx.StaticLine( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL )
        mainSizer.Add( self.m_sl2, 0, wx.EXPAND, 0 )

        self.lpane = PFWidgetsContainer(self)
        mainSizer.Add(self.lpane, 1, wx.EXPAND)
        self.SetSizer(mainSizer)
        self.Layout()
        self.Show()

        self.Bind(wx.EVT_SIZE, self.SizeRefreshList)
        self.Bind(EVT_SB_STAGE2_SEL, self.stage2)
        self.Bind(EVT_SB_STAGE1_SEL, self.stage1)
        self.Bind(EVT_SB_STAGE3_SEL, self.stage3)
        self.Bind(EVT_SB_SEARCH_SEL, self.searchStage)

        self.mainFrame.Bind(GE.FIT_CHANGED, self.RefreshList)

        self.stage1(None)

    def RefreshContent(self):
        stage = self.GetActiveStage()
        if stage == 1:
            return
        stageData = self.GetStageData(stage)
        self.hpane.gotoStage(stage, stageData)

    def RefreshList(self, event):
        stage = self.GetActiveStage()
        if stage == 3 or stage == 4:
            self.lpane.RefreshList(True)
        event.Skip()

    def SizeRefreshList(self, event):
        ewidth, eheight = event.GetSize()
        self.Layout()
        self.lpane.Layout()
        self.lpane.RefreshList(True)
        event.Skip()

    def __del__(self):
        pass

    def GetActiveStage(self):
        return self._activeStage

    def GetLastStage(self):
        return self._lastStage

    def GetStageData(self, stage):
        if stage == 1:
            return self._stage1Data
        if stage == 2:
            return self._stage2Data
        if stage == 3:
            return self._stage3Data
        return -1

    def GetStage3ShipName(self):
        return self._stage3ShipName

    def nameKey(self, info):
        return info[1]

    def stage1(self, event):
        self._lastStage = self._activeStage
        self._activeStage = 1
        self.lastdata = 0
        self.hpane.ToggleNewFitSB(False)
        self.hpane.ToggleFitViewModeSB(False)
        sMarket = service.Market.getInstance()
        self.lpane.RemoveAllChildren()
        if len(self.categoryList) == 0:
            self.categoryList = sMarket.getShipRoot()
            self.categoryList.sort(key=self.nameKey)
        for ID, name in self.categoryList:
            self.lpane.AddWidget(CategoryItem(self.lpane, ID, (name, 0)))

        self.lpane.RefreshList()

    RACE_ORDER = ["amarr", "caldari", "gallente", "minmatar", "ore", "serpentis", "angel", "blood", "sansha", "guristas", None]
    def raceNameKey(self, shipInfo):
        return self.RACE_ORDER.index(shipInfo[2]), shipInfo[1]

    def stage2Callback(self,data):
        if self.GetActiveStage() != 2:
            return
        categoryID, shipList = data
        sFit = service.Fit.getInstance()

        shipList.sort(key=self.raceNameKey)
        for ID, name, race in shipList:
            fits = len(sFit.getFitsWithShip(ID))
            if self.filterShipsWithNoFits:
                if fits>0:
                    self.lpane.AddWidget(ShipItem(self.lpane, ID, (name, fits), race))
            else:
                self.lpane.AddWidget(ShipItem(self.lpane, ID, (name, fits), race))

        self.lpane.RefreshList()

    def stage2(self, event):
        back = event.back
        if not back:
            self.browseHist.append( (1,0) )
        self._lastStage = self._activeStage
        self._activeStage = 2
        categoryID = event.categoryID
        self.lastdata = categoryID


        self.lpane.RemoveAllChildren()
        sMarket = service.Market.getInstance()
        sMarket.getShipListDelayed(self.stage2Callback, categoryID)

        self._stage2Data = categoryID
        self.hpane.ToggleNewFitSB(False)
        self.hpane.ToggleFitViewModeSB(True)

    def stage3(self, event):
        if event.back == 0:
            self.browseHist.append( (2,self._stage2Data) )
        elif event.back == -1:
            if len(self.hpane.recentSearches)>0:
                self.browseHist.append((4, self.hpane.lastSearch))

        shipID = event.shipID
        self.lastdata = shipID
        self._lastStage = self._activeStage
        self._activeStage = 3

        sFit = service.Fit.getInstance()
        sMarket = service.Market.getInstance()
        self.lpane.RemoveAllChildren()
        fitList = sFit.getFitsWithShip(shipID)

        if len(fitList) == 0:
            stage,data = self.browseHist.pop()
            self.hpane.gotoStage(stage,data)
            return
        self.hpane.ToggleFitViewModeSB(False)
        self.hpane.ToggleNewFitSB(True)
        fitList.sort(key=self.nameKey)
        shipName = sMarket.getItem(shipID).name

        self._stage3ShipName = shipName
        self._stage3Data = shipID

        for ID, name, timestamp in fitList:
            self.lpane.AddWidget(FitItem(self.lpane, ID, (shipName, name, timestamp),shipID))

        self.lpane.RefreshList()

    def searchStage(self, event):
        if not event.back:
            if self._activeStage !=4:
                if len(self.browseHist) >0:
                    self.browseHist.append( (self._activeStage, self.lastdata) )
                else:
                    self.browseHist.append((1,0))
            self._lastStage = self._activeStage
            self._activeStage = 4

        sMarket = service.Market.getInstance()
        sFit = service.Fit.getInstance()
        query = event.text

        self.lpane.RemoveAllChildren()
        if query:
            shipList = sMarket.searchShips(query)
            fitList = sFit.searchFits(query)

            for ID, name, race in shipList:
                self.lpane.AddWidget(ShipItem(self.lpane, ID, (name, len(sFit.getFitsWithShip(ID))), race))

            for ID, name, shipID, shipName,timestamp in fitList:
                self.lpane.AddWidget(FitItem(self.lpane, ID, (shipName, name,timestamp), shipID))
            if len(shipList) == 0 and len(fitList) == 0 :
                self.lpane.AddWidget(PFStaticText(self.lpane, label = "No matching results."))
            self.lpane.RefreshList()

class PFStaticText(wx.StaticText):
    def _init__(self,parent, label = wx.EmptyString):
        wx.StaticText(self,parent,label)

    def GetType(self):
        return -1

class PFGenBitmapButton(GenBitmapButton):
    def __init__(self, parent, id, bitmap, pos, size, style):
        GenBitmapButton.__init__(self, parent, id, bitmap, pos, size, style)
        self.bgcolor = wx.Brush(wx.WHITE)

    def SetBackgroundColour(self, color):
        self.bgcolor = wx.Brush(color)

    def GetBackgroundBrush(self, dc):
        return self.bgcolor

class HeaderPane (wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__ (self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.Size(500, 32), style=wx.TAB_TRAVERSAL)

        self.mainFrame = gui.mainFrame.MainFrame.getInstance()

        self.rewBmp = bitmapLoader.getBitmap("frewind_small","icons")
        self.forwBmp = bitmapLoader.getBitmap("fforward_small","icons")
        self.searchBmp = bitmapLoader.getBitmap("fsearch_small","icons")
        self.newBmp = bitmapLoader.getBitmap("fit_add_small","icons")
        self.resetBmp = bitmapLoader.getBitmap("freset_small","icons")
        self.switchBmp = bitmapLoader.getBitmap("fit_switch_view_mode_small","icons")

        img = self.newBmp.ConvertToImage()
        img.RotateHue(0.625)
        self.newBmp = wx.BitmapFromImage(img)

        img = self.switchBmp.ConvertToImage()
        img.RotateHue(0.625)
        self.switchSelBmp = wx.BitmapFromImage(img)

        img = self.switchBmp.ConvertToImage()
        img.RotateHue(0.500)
        self.switchHoverBmp = wx.BitmapFromImage(img)

        img = self.rewBmp.ConvertToImage()
        img.RotateHue(0.625)
        self.rewHoverBmp = wx.BitmapFromImage(img)

        img = self.resetBmp.ConvertToImage()
        img.RotateHue(-1)
        self.resetHoverBmp = wx.BitmapFromImage(img)

        img = self.searchBmp.ConvertToImage()
        img.RotateHue(0.625)
        self.searchHoverBmp = wx.BitmapFromImage(img)

        img = self.newBmp.ConvertToImage()
        img.RotateHue(0.350)
        self.newHoverBmp = wx.BitmapFromImage(img)


        self.shipBrowser = self.Parent

        self.toggleSearch = -1
        self.recentSearches = []
        self.lastSearch = ""
        self.menu = None
        self.inPopup = False
        self.inSearch = False

        bmpSize = (16,16)
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )

        mainSizer = wx.BoxSizer(wx.HORIZONTAL)

        if 'wxMac' in wx.PlatformInfo:
            bgcolour = wx.Colour(0, 0, 0, 0)
        else:
            bgcolour = wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE )

        self.sbReset = PFGenBitmapButton( self, wx.ID_ANY, self.resetBmp, wx.DefaultPosition, bmpSize, wx.BORDER_NONE )
        mainSizer.Add(self.sbReset, 0, wx.LEFT | wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER_VERTICAL , 5)
        self.sbReset.SetBackgroundColour( bgcolour )
        self.sbReset.SetBitmapSelected(self.resetBmp)

        self.sbRewind = PFGenBitmapButton( self, wx.ID_ANY, self.rewBmp, wx.DefaultPosition, bmpSize, wx.BORDER_NONE )
        mainSizer.Add(self.sbRewind, 0, wx.LEFT | wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER_VERTICAL , 5)
        self.sbRewind.SetBackgroundColour( bgcolour )
        self.sbRewind.SetBitmapSelected(self.rewBmp)

        self.sl1 = wx.StaticLine( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_VERTICAL )
        mainSizer.Add( self.sl1, 0, wx.EXPAND |wx.LEFT, 5 )

        self.sbNewFit = PFGenBitmapButton( self, wx.ID_ANY, self.newBmp, wx.DefaultPosition, bmpSize, wx.BORDER_NONE )
        mainSizer.Add(self.sbNewFit, 0, wx.LEFT | wx.TOP | wx.BOTTOM  | wx.ALIGN_CENTER_VERTICAL , 5)
        self.sbNewFit.SetBackgroundColour( bgcolour )

        self.sbSwitchFitView = PFGenBitmapButton( self, wx.ID_ANY, self.switchBmp, wx.DefaultPosition, bmpSize, wx.BORDER_NONE )
        mainSizer.Add(self.sbSwitchFitView, 0, wx.LEFT | wx.TOP | wx.BOTTOM  | wx.ALIGN_CENTER_VERTICAL , 5)
        self.sbSwitchFitView.SetBackgroundColour( bgcolour )


        self.stStatus = wx.StaticText( self, wx.ID_ANY, "", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.stStatus.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
        self.stStatus.Wrap( -1 )
        mainSizer.Add(self.stStatus, 1, wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL , 5)

        self.spanel = wx.Panel(self)
        self.spanel.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )

        spsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.spanel.SetSizer(spsizer)

        self.search = wx.TextCtrl(self.spanel, wx.ID_ANY, "", style=wx.TE_PROCESS_ENTER )


        spsizer.Add(self.search,1, wx.ALIGN_CENTER_VERTICAL)
        mainSizer.Add(self.spanel,1000,wx.EXPAND | wx.LEFT, 5)

        self.sbSearch = PFGenBitmapButton( self, wx.ID_ANY, self.searchBmp, wx.DefaultPosition, bmpSize, wx.BORDER_NONE )
        mainSizer.Add(self.sbSearch, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL , 5)
        self.sbSearch.SetBackgroundColour( bgcolour )

        self.SetSizer(mainSizer)

        self.sbReset.Bind(wx.EVT_BUTTON,self.OnReset)
        self.sbReset.Bind( wx.EVT_ENTER_WINDOW, self.OnEnterWReset )
        self.sbReset.Bind( wx.EVT_LEAVE_WINDOW, self.OnLeaveWReset )

        self.sbRewind.Bind(wx.EVT_BUTTON,self.OnBack)
        self.sbRewind.Bind( wx.EVT_ENTER_WINDOW, self.OnEnterWRewind )
        self.sbRewind.Bind( wx.EVT_LEAVE_WINDOW, self.OnLeaveWRewind )


        self.sbSearch.Bind(wx.EVT_BUTTON,self.OnSearch)
        self.sbSearch.Bind( wx.EVT_ENTER_WINDOW, self.OnEnterWSearch )
        self.sbSearch.Bind( wx.EVT_LEAVE_WINDOW, self.OnLeaveWSearch )

        self.sbNewFit.Bind(wx.EVT_BUTTON,self.OnNewFitting)
        self.sbNewFit.Bind( wx.EVT_ENTER_WINDOW, self.OnEnterWNewFit )
        self.sbNewFit.Bind( wx.EVT_LEAVE_WINDOW, self.OnLeaveWNewFit )

        self.sbSwitchFitView.Bind(wx.EVT_BUTTON,self.OnSwitch)
        self.sbSwitchFitView.Bind( wx.EVT_ENTER_WINDOW, self.OnEnterWSwitch )
        self.sbSwitchFitView.Bind( wx.EVT_LEAVE_WINDOW, self.OnLeaveWSwitch )

        self.search.Bind(wx.EVT_TEXT_ENTER, self.doSearch)
        self.search.Bind(wx.EVT_KILL_FOCUS, self.editLostFocus)
        self.search.Bind(wx.EVT_KEY_DOWN, self.editCheckEsc)
        self.search.Bind(wx.EVT_CONTEXT_MENU,self.OnMenu)
        self.search.Bind(wx.EVT_TEXT, self.scheduleSearch)

        self.sbSearch.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.sbSearch.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

        self.Layout()
        self.spanel.Hide()
        self.search.Hide()

    def OnLeftDown(self, event):
        self.inPopup = True
        event.Skip()

    def OnLeftUp(self, event):
        self.inPopup = False
        event.Skip()

    def scheduleSearch(self, event):
        if self.inPopup:
            return
        search = self.search.GetValue()
        if len(search) < 3 and len(search) > 0:
            if self.inSearch == True:
                self.inSearch = False
                if len(self.shipBrowser.browseHist) > 0:
                    stage,data = self.shipBrowser.browseHist.pop()
                    self.gotoStage(stage,data)
        else:
            if search:
                wx.PostEvent(self.shipBrowser,SearchSelected(text=search, back = False))
                self.inSearch = True
            else:
                self.inSearch = False

        event.Skip()

    def OnMenu(self, event):
        self.inPopup = True
        self.menu = self.MakeMenu()
        self.PopupMenu(self.menu)
        self.inPopup = False
        pass

    def OnMenuSelected(self, event):
        item = self.menu.FindItemById(event.GetId())
        text = item.GetText()

        if len(text)>2 :
            wx.PostEvent(self.shipBrowser,SearchSelected(text=text, back = False))
        self.editLostFocus()

    def MakeMenu(self):
        menu = wx.Menu()
        normalCMItems = ["Undo","_sep_", "Cut", "Copy","Paste","Delte","_sep_", "Select All"]
        item = menu.Append(-1, "Recent")
        item.Enable(False)

        if len(self.recentSearches) > 0:
            menu.AppendSeparator()
        for txt in self.recentSearches:
            if txt:
                item = menu.Append(-1, txt)
                menu.Bind(wx.EVT_MENU, self.OnMenuSelected, item)

        return menu


    def editLostFocus(self, event = None):
        if self.inPopup:
            return
        if self.toggleSearch == 1:
            self.search.Show(False)
            self.spanel.Show(False)
            self.toggleSearch = -1

        stxt = self.search.GetValue()
        if stxt not in self.recentSearches:
            if stxt:
                self.recentSearches.append(stxt)
                self.lastSearch = stxt
        if len(self.recentSearches) >5:
            self.recentSearches.remove(self.recentSearches[0])
        self.search.SetValue("")

    def editCheckEsc(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.search.Show(False)
            self.spanel.Show(False)
            self.toggleSearch = -1
        else:
            event.Skip()

    def doSearch(self, event):
        stxt = self.search.GetValue()
        if len(stxt) > 2:
            self.editLostFocus()

    def ToggleNewFitSB(self, toggle):
        self.sbNewFit.Show(toggle)
        self.Layout()

    def ToggleFitViewModeSB(self, toggle):
        self.sbSwitchFitView.Show(toggle)
        self.Layout()

    def OnReset(self,event):
        if self.shipBrowser.browseHist:
            self.shipBrowser.browseHist = []
            self.gotoStage(1,0)
            self.stStatus.SetLabel("")
            self.Layout()
        event.Skip()

    def OnEnterWReset(self, event):
        if self.shipBrowser.browseHist:
            self.stStatus.Enable()
        else:
            self.stStatus.Disable()
        if self.toggleSearch != 1:
            self.stStatus.SetLabel("Ship Groups")
        self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        self.sbReset.SetBitmapLabel(self.resetHoverBmp, False)
        self.sbReset.Refresh()
        event.Skip()

    def OnLeaveWReset(self, event):
        self.stStatus.SetLabel("")
        self.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
        self.sbReset.SetBitmapLabel(self.resetBmp, False)
        self.sbReset.Refresh()
        event.Skip()

    def OnEnterWForward(self, event):
        if self.toggleSearch != 1:
            self.stStatus.SetLabel("Forward")
        stage = self.Parent.GetActiveStage()

        if stage < 3:
            if self.Parent.GetStageData(stage+1) != -1:
                self.stStatus.Enable()
            else:
                self.stStatus.Disable()
        else:
            self.stStatus.Disable()

        self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        event.Skip()

    def OnLeaveWForward(self, event):
        self.stStatus.Enable()
        self.stStatus.SetLabel("")
        self.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
        event.Skip()

    def OnEnterWRewind(self, event):
        if self.toggleSearch != 1:
            self.stStatus.SetLabel("Back")

        stage = self.Parent.GetActiveStage()

        if stage > 1:
            self.stStatus.Enable()
        else:
            self.stStatus.Disable()

        self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        event.Skip()

    def OnLeaveWRewind(self, event):
        self.stStatus.Enable()
        self.stStatus.SetLabel("")
        self.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
        event.Skip()

    def OnEnterWSearch(self, event):
        if self.toggleSearch != 1:
            self.stStatus.SetLabel("Search fittings")
        self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        self.sbSearch.SetBitmapLabel(self.searchHoverBmp, False)
        self.Refresh()
        event.Skip()

    def OnLeaveWSearch(self, event):
        self.stStatus.SetLabel("")
        self.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
        self.sbSearch.SetBitmapLabel(self.searchBmp, False)
        self.Refresh()
        event.Skip()

    def OnEnterWSwitch(self, event):
        if self.toggleSearch != 1:
            self.stStatus.SetLabel("Show empty ship groups" if self.shipBrowser.filterShipsWithNoFits else "Hide empty ship groups")
        self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        self.sbSwitchFitView.SetBitmapLabel(self.switchHoverBmp, False)
        self.Refresh()
        event.Skip()

    def OnLeaveWSwitch(self, event):
        self.stStatus.SetLabel("")
        self.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
        self.sbSwitchFitView.SetBitmapLabel(self.switchBmp if not self.shipBrowser.filterShipsWithNoFits else self.switchSelBmp, False)
        self.Refresh()
        event.Skip()

    def OnEnterWNewFit(self, event):
        if self.toggleSearch != 1:
            self.stStatus.SetLabel("New fitting")
        self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        self.sbNewFit.SetBitmapLabel(self.newHoverBmp, False)
        self.Refresh()
        event.Skip()

    def OnLeaveWNewFit(self, event):
        self.stStatus.SetLabel("")
        self.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
        self.sbNewFit.SetBitmapLabel(self.newBmp, False)
        self.Refresh()
        event.Skip()

    def OnSearch(self, event):
        self.stStatus.SetLabel("")
        if self.toggleSearch == 2:
            self.toggleSearch = -1
            return
        if not self.search.IsShown():
            self.spanel.Show(True)
            self.search.Show(True)
            self.search.SetFocus()
            self.toggleSearch = 1
            self.Layout()
            self.spanel.Layout()

        else:
            self.search.Show(False)
            self.spanel.Show(False)
            self.toggleSearch = -1
            self.Layout()
        event.Skip()

    def OnSwitch(self, event):
        if self.shipBrowser.filterShipsWithNoFits:
            self.shipBrowser.filterShipsWithNoFits = False
            self.sbSwitchFitView.SetBitmapLabel(self.switchBmp,False)
        else:
            self.shipBrowser.filterShipsWithNoFits = True
            self.sbSwitchFitView.SetBitmapLabel(self.switchSelBmp,False)
        self.stStatus.SetLabel("Show empty ship groups" if self.shipBrowser.filterShipsWithNoFits else "Hide empty ship groups")
        stage = self.shipBrowser.GetActiveStage()
        if stage == 2:
            categoryID = self.shipBrowser.GetStageData(stage)
            wx.PostEvent(self.shipBrowser,Stage2Selected(categoryID=categoryID, back = True))
        event.Skip()

    def OnNewFitting(self, event):
        self.editLostFocus()
        stage = self.Parent.GetActiveStage()
        if stage == 3:
            shipID = self.Parent.GetStageData(stage)
            shipName = self.Parent.GetStage3ShipName()
            sFit = service.Fit.getInstance()
            fitID = sFit.newFit(shipID, "%s fit" %shipName)
            self.shipBrowser.fitIDMustEditName = fitID
            wx.PostEvent(self.Parent,Stage3Selected(shipID=shipID, back = True))
            wx.PostEvent(self.mainFrame, FitSelected(fitID=fitID))
        event.Skip()

    def OnForward(self,event):
        self.editLostFocus()
        stage = self.Parent.GetActiveStage()
        stage +=1
        if stage >3:
            stage = 3
            return
        self.gotoStage(stage)

        self.stStatus.Enable()
        self.stStatus.SetLabel("")

        event.Skip()

    def OnBack(self,event):

        self.stStatus.Enable()
        self.stStatus.SetLabel("")
        if len(self.shipBrowser.browseHist) > 0:
            stage,data = self.shipBrowser.browseHist.pop()
            self.gotoStage(stage,data)
        event.Skip()

    def gotoStage(self,stage, data = None):
        if stage == 1:
            wx.PostEvent(self.Parent,Stage1Selected())
        elif stage == 2:
            wx.PostEvent(self.Parent,Stage2Selected(categoryID=data, back = True))
        elif stage == 3:
            wx.PostEvent(self.Parent,Stage3Selected(shipID=data, back = 1))
        elif stage == 4:
            self.shipBrowser._activeStage = 4
            self.stStatus.SetLabel("Search: %s" % data.capitalize())
            self.Layout()
            wx.PostEvent(self.Parent,SearchSelected(text=data, back = True))
        else:
            wx.PostEvent(self.Parent,Stage1Selected())


class PFBaseButton(object):
    def __init__(self, normalBitmap = wx.NullBitmap,label = "", callback = None, hoverBitmap = None, disabledBitmap = None):

        self.normalBmp = normalBitmap
        self.hoverBmp = hoverBitmap
        self.disabledBmp = disabledBitmap
        self.label = label

        self.callback = callback

        self.state = BTN_NORMAL
        # state : BTN_STUFF

    def SetCallback(self, callback):
        self.callback = callback

    def GetCallback(self):
        return self.callback

    def DoCallback(self):
        if self.callback:
            self.callback()

    def SetState(self, state = BTN_NORMAL):
        self.state = state

    def GetState(self):
        return self.state

    def GetSize(self):
        w = self.normalBmp.GetWidth()
        h = self.normalBmp.GetHeight()
        return (w,h)

    def GetBitmap(self):
        return self.normalBmp

    def SetBitmap(self, bitmap):
        self.normalBmp = bitmap

    def GetLabel(self):
        return self.label

    def GetHoverBitmap(self):
        if self.hoverBmp == None:
            return self.normalBmp
        return self.hoverBmp

    def GetDisabledBitmap(self):
        if self.disabledBmp == None:
            return self.normalBmp
        return self.disabledBmp

class PFToolbar(object):
    def __init__(self):
        self.buttons =[]
        self.toolbarX = 0
        self.toolbarY = 0
        self.padding = 2
        self.hoverLabel = ""

    def SetPosition(self, pos):
        self.toolbarX, self.toolbarY = pos

    def AddButton(self, btnBitmap, label = "", clickCallback = None, hoverBitmap = None, disabledBitmap = None):
        btn = PFBaseButton(btnBitmap, label, clickCallback, hoverBitmap, disabledBitmap)
        self.buttons.append(btn)
        return btn

    def ClearState(self):
        for button in self.buttons:
            button.SetState()
        self.hoverLabel = ""

    def MouseMove(self, event):
        doRefresh = False
        bx = self.toolbarX
        self.hoverLabel = ""

        for button in self.buttons:
            state = button.GetState()
            if self.HitTest( (bx, self.toolbarY), event.GetPosition(), button.GetSize()):
                if not state & BTN_HOVER:
                    button.SetState(state | BTN_HOVER)
                    self.hoverLabel = button.GetLabel()
                    doRefresh = True
            else:
                if state & BTN_HOVER:
                    button.SetState(state ^ BTN_HOVER)
                    doRefresh = True

            bwidth, bheight = button.GetSize()
            bx += bwidth + self.padding
        return doRefresh

    def MouseClick(self, event):
        mx,my = event.GetPosition()
        bx = self.toolbarX
        for button in self.buttons:
            state = button.GetState()
            if state & BTN_PRESSED:
                button.SetState(state ^ BTN_PRESSED )
                if self.HitTest( (bx, self.toolbarY), event.GetPosition(), button.GetSize()):
                    return button
                else:
                    return False
            bwidth, bheight = button.GetSize()
            bx += bwidth + self.padding

        bx = self.toolbarX
        for button in self.buttons:
            state = button.GetState()
            if self.HitTest( (bx, self.toolbarY), event.GetPosition(), button.GetSize()):

                if event.LeftDown() or event.LeftDClick():
                    button.SetState(state | BTN_PRESSED)
                    return button

                elif event.LeftUp():
                    button.SetState(state | (not BTN_PRESSED))
                    return button

            bwidth, bheight = button.GetSize()
            bx += bwidth + self.padding
        return None

    def GetWidth(self):
        bx = 0
        for button in self.buttons:
            bwidth, bheight = button.GetSize()
            bx += bwidth + self.padding
        return bx

    def GetHeight(self):
        height = 0
        for button in self.buttons:
            bwidth, bheight = button.GetSize()
            height = max(height, bheight)
        return height

    def HitTest(self, target, position, area):
        x, y = target
        px, py = position
        aX, aY = area
        if (px > x and px < x + aX) and (py > y and py < y + aY):
            return True
        return False

    def Render(self, pdc):
        bx = self.toolbarX
        for button in self.buttons:
            by = self.toolbarY
            tbx = bx

            btnState = button.GetState()

            bmp = button.GetDisabledBitmap()

            if btnState & BTN_NORMAL:
                bmp = button.GetBitmap()

            if btnState & BTN_HOVER:
                bmp = button.GetHoverBitmap()

            if btnState & BTN_PRESSED:
                bmp = button.GetBitmap()
                by += self.padding / 2
                tbx += self.padding / 2

            bmpWidth = bmp.GetWidth()
            pdc.DrawBitmap(bmp, tbx, by)
            bx += bmpWidth + self.padding

class SBItem(wx.Window):
    def __init__(self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition, size = (0,16), style = 0):
        wx.Window.__init__(self, parent, id, pos, size, style)

        self.highlighted = False
        self.selected = False
        self.bkBitmap = None
        self.toolbar = PFToolbar()


        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

        if "wxMSW" in wx.PlatformInfo:
            self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDown)


        self.Bind(wx.EVT_LEFT_DOWN,self.OnLeftDown)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnEnterWindow)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)
        self.Bind(wx.EVT_MOTION, self.OnMotion)

    def Refresh(self):
        self.RenderBackground()
        wx.Window.Refresh(self)

    def OnPaint(self, event):
        mdc = wx.BufferedPaintDC(self)

        if self.bkBitmap is None:
            self.RenderBackground()

        mdc.DrawBitmap(self.bkBitmap, 0,0)

        self.DrawItem(mdc)
        self.toolbar.Render(mdc)

    def DrawItem(self, mdc):
        pass

    def OnEraseBackground(self, event):
        pass

    def MouseLeftUp(self, event):
        pass

    def MouseLeftDown(self, event):
        pass

    def MouseMove(self, event):
        pass

    def OnLeftUp(self, event):
        if self.HasCapture():
            self.ReleaseMouse()

        btn = self.toolbar.MouseClick(event)

        if btn is not None:
            if btn is not False:
                if btn.GetState() & BTN_NORMAL:
                    btn.DoCallback()
                    self.Refresh()
            else:
                self.Refresh()
            return

        self.MouseLeftUp(event)


    def OnLeftDown(self, event):
        self.CaptureMouse()

        btn = self.toolbar.MouseClick(event)

        if btn is not None:
            if btn.GetState() & BTN_PRESSED:
                self.Refresh()
            return

        self.MouseLeftDown(event)

    def OnEnterWindow(self, event):
        self.SetHighlighted(True)
        self.toolbar.ClearState()
        self.Refresh()
        event.Skip()

    def OnLeaveWindow(self, event):
        mposx, mposy = wx.GetMousePosition()
        rect = self.GetRect()
        rect.top = rect.left = 0
        cx,cy = self.ScreenToClient((mposx,mposy))
        if not rect.Contains((cx,cy)):
            self.SetHighlighted(False)
            self.toolbar.ClearState()
            self.Refresh()
        event.Skip()

    def OnMotion(self, event):
        if self.toolbar.MouseMove(event):
            self.Refresh()

        self.MouseMove(event)

        event.Skip()

    def GetType(self):
        return -1

    def SetSelected(self, select = True):
        self.selected = select

    def SetHighlighted(self, highlight = True):
        self.highlighted = highlight

    def GetState(self):

        if self.highlighted and not self.selected:
            state = SB_ITEM_HIGHLIGHTED

        elif self.selected:
            if self.highlighted:
                state = SB_ITEM_SELECTED  | SB_ITEM_HIGHLIGHTED
            else:
                state = SB_ITEM_SELECTED
        else:
            state = SB_ITEM_NORMAL

        return state

    def RenderBackground(self):
        rect = self.GetRect()

        windowColor = wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW)

        state = self.GetState()

        sFactor = 0.2
        mFactor = None
        eFactor = 0

        if state == SB_ITEM_HIGHLIGHTED:
            mFactor = 0.55

        elif state == SB_ITEM_SELECTED  | SB_ITEM_HIGHLIGHTED:
            eFactor = 0.3
        elif state == SB_ITEM_SELECTED:
            eFactor = 0.15
        else:
            sFactor = 0

        if self.bkBitmap:
            if self.bkBitmap.eFactor == eFactor and self.bkBitmap.sFactor == sFactor and self.bkBitmap.mFactor == mFactor \
             and rect.width == self.bkBitmap.GetWidth() and rect.height == self.bkBitmap.GetHeight() :
                return
            else:
                del self.bkBitmap

        self.bkBitmap = drawUtils.RenderGradientBar(windowColor, rect.width, rect.height, sFactor, eFactor, mFactor)
        self.bkBitmap.state = state
        self.bkBitmap.sFactor = sFactor
        self.bkBitmap.eFactor = eFactor
        self.bkBitmap.mFactor = mFactor

class CategoryItem(SBItem):
    def __init__(self,parent, categoryID, fittingInfo, size = (0,16)):
        SBItem.__init__(self,parent,size = size)

        if categoryID:
            self.shipBmp = bitmapLoader.getBitmap("ship_small","icons")
        else:
            self.shipBmp = wx.EmptyBitmap(16,16)

        self.categoryID = categoryID
        self.fittingInfo = fittingInfo
        self.shipBrowser = self.Parent.Parent

        self.padding = 4

        self.fontBig = wx.FontFromPixelSize((0,15),wx.SWISS, wx.NORMAL, wx.NORMAL, False)

        self.animTimerId = wx.NewId()
        self.animCount = 100
        self.animTimer = wx.Timer(self, self.animTimerId)
        self.animStep = 0
        self.animPeriod = 10
        self.animDuration = 100

        self.Bind(wx.EVT_TIMER, self.OnTimer)
        self.animTimer.Start(self.animPeriod)


    def OnTimer(self, event):
        step = self.OUT_QUAD(self.animStep, 0, 10, self.animDuration)
        self.animCount = 10 - step
        self.animStep += self.animPeriod
        if self.animStep > self.animDuration or self.animCount < 0 :
            self.animCount = 0
            self.animTimer.Stop()
        self.Refresh()

    def OUT_QUAD (self, t, b, c, d):
        t=float(t)
        b=float(b)
        c=float(c)
        d=float(d)

        t/=d

        return -c *(t)*(t-2) + b

    def GetType(self):
        return 1

    def MouseLeftUp(self, event):

        categoryID = self.categoryID
        wx.PostEvent(self.shipBrowser,Stage2Selected(categoryID=categoryID, back=False))

    def UpdateElementsPos(self, mdc):
        rect = self.GetRect()
        self.shipBmpx = self.padding
        self.shipBmpy = (rect.height-self.shipBmp.GetWidth())/2

        self.shipBmpx -= self.animCount

        mdc.SetFont(self.fontBig)
        categoryName, fittings = self.fittingInfo
        wtext, htext = mdc.GetTextExtent(categoryName)


        self.catx = self.shipBmpx + self.shipBmp.GetWidth() + self.padding
        self.caty = (rect.height - htext) / 2

    def DrawItem(self, mdc):
        rect = self.GetRect()

        self.UpdateElementsPos(mdc)

        windowColor = wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW)
        textColor = colorUtils.GetSuitableColor(windowColor, 1)

        mdc.SetTextForeground(textColor)

        mdc.DrawBitmap(self.shipBmp,self.shipBmpx,self.shipBmpy,0)

        mdc.SetFont(self.fontBig)

        categoryName, fittings = self.fittingInfo

        mdc.DrawText(categoryName, self.catx, self.caty)

#===============================================================================
#        Waiting for total #fits impl in eos/service
#
#        mdc.SetFont(wx.Font(8, wx.SWISS, wx.NORMAL, wx.NORMAL, False))
#
#        if fittings <1:
#            fformat = "No fits"
#        else:
#            if fittings == 1:
#                fformat = "%d fit"
#            else:
#                fformat = "%d fits"
#
#        if fittings>0:
#            xtext, ytext = mdc.GetTextExtent(fformat % fittings)
#            ypos = (rect.height - ytext)/2
#        else:
#            xtext, ytext = mdc.GetTextExtent(fformat)
#            ypos = (rect.height - ytext)/2
#===============================================================================


class ShipItem(SBItem):
    def __init__(self, parent, shipID=None, shipFittingInfo=("Test", 2), itemData=None,
                 id=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=(0, 40), style=0):
        SBItem.__init__(self, parent, size = size)

        self.mainFrame = gui.mainFrame.MainFrame.getInstance()

        self._itemData = itemData

        self.shipRace = itemData

        self.shipID = shipID

        self.fontBig = wx.FontFromPixelSize((0,15),wx.SWISS, wx.NORMAL, wx.BOLD, False)
        self.fontNormal = wx.FontFromPixelSize((0,14),wx.SWISS, wx.NORMAL, wx.NORMAL, False)
        self.fontSmall = wx.FontFromPixelSize((0,12),wx.SWISS, wx.NORMAL, wx.NORMAL, False)

        self.shipBmp = None
        if shipID:
            self.shipBmp = bitmapLoader.getBitmap(str(shipID),"ships")
        if not self.shipBmp:
            self.shipBmp = bitmapLoader.getBitmap("ship_no_image_big","icons")

        self.shipFittingInfo = shipFittingInfo
        self.shipName, self.shipFits = shipFittingInfo

        self.newBmp = bitmapLoader.getBitmap("fit_add_small", "icons")
        self.acceptBmp = bitmapLoader.getBitmap("faccept_small", "icons")

        self.shipEffBk = bitmapLoader.getBitmap("fshipbk_big","icons")
        self.raceBmp = bitmapLoader.getBitmap("race_%s_small" % self.shipRace, "icons")

        if self.shipName == "Apotheosis":
            self.raceMBmp = bitmapLoader.getBitmap("race_jove_small","icons")
        else:
            self.raceMBmp = bitmapLoader.getBitmap("fit_delete_small","icons")

        if not self.raceBmp:
            self.raceBmp = self.raceMBmp

        self.shipBrowser = self.Parent.Parent

        self.editWidth = 150
        self.padding = 4

        self.tcFitName = wx.TextCtrl(self, wx.ID_ANY, "%s fit" % self.shipName, wx.DefaultPosition, (120,-1), wx.TE_PROCESS_ENTER)
        self.tcFitName.Show(False)


        self.newBtn = self.toolbar.AddButton(self.newBmp,"New", self.newBtnCB)

        self.tcFitName.Bind(wx.EVT_TEXT_ENTER, self.createNewFit)
        self.tcFitName.Bind(wx.EVT_KILL_FOCUS, self.editLostFocus)
        self.tcFitName.Bind(wx.EVT_KEY_DOWN, self.editCheckEsc)

        self.animTimerId = wx.NewId()
        self.animCount = 100
        self.animTimer = wx.Timer(self, self.animTimerId)
        self.animStep = 0
        self.animPeriod = 10
        self.animDuration = 100
        if self.shipBrowser.GetActiveStage() != 4 and self.shipBrowser.GetLastStage() !=2:
            self.Bind(wx.EVT_TIMER, self.OnTimer)
            self.animTimer.Start(self.animPeriod)
        else:
            self.animCount = 0

    def OnTimer(self, event):
        step = self.OUT_QUAD(self.animStep, 0, 10, self.animDuration)
        self.animCount = 10 - step
        self.animStep += self.animPeriod
        if self.animStep > self.animDuration or self.animCount < 0 :
            self.animCount = 0
            self.animTimer.Stop()
        self.Refresh()

    def OUT_QUAD (self, t, b, c, d):
        t=float(t)
        b=float(b)
        c=float(c)
        d=float(d)

        t/=d

        return -c *(t)*(t-2) + b

    def GetType(self):
        return 2

    def MouseLeftUp(self, event):
        if self.tcFitName.IsShown():
            self.tcFitName.Show(False)
            self.newBtn.SetBitmap(self.newBmp)
            self.Refresh()
        else:
            shipName, fittings = self.shipFittingInfo
            if fittings > 0:
                wx.PostEvent(self.shipBrowser,Stage3Selected(shipID=self.shipID, back = -1 if self.shipBrowser.GetActiveStage() == 4 else 0))
            else:
                self.newBtnCB()

    def newBtnCB(self):
        if self.tcFitName.IsShown():
            self.tcFitName.Show(False)
            self.createNewFit()
        else:
            self.tcFitName.SetValue("%s fit" % self.shipName)
            self.tcFitName.Show()

            self.tcFitName.SetFocus()
            self.tcFitName.SelectAll()

            self.newBtn.SetBitmap(self.acceptBmp)

            self.Refresh()

    def editLostFocus(self, event):
        self.tcFitName.Show(False)
        self.newBtn.SetBitmap(self.newBmp)
        self.Refresh()

    def editCheckEsc(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.tcFitName.Show(False)
        else:
            event.Skip()

    def createNewFit(self, event=None):
        self.tcFitName.Show(False)

        sFit = service.Fit.getInstance()
        fitID = sFit.newFit(self.shipID, self.tcFitName.GetValue())

        wx.PostEvent(self.shipBrowser,Stage3Selected(shipID=self.shipID, back=False))
        wx.PostEvent(self.mainFrame, FitSelected(fitID=fitID))

    def UpdateElementsPos(self, mdc):
        rect = self.GetRect()

        self.toolbarx = rect.width - self.toolbar.GetWidth() - self.padding
        self.toolbary = (rect.height - self.toolbar.GetHeight()) / 2

        self.toolbarx = self.toolbarx + self.animCount

        self.shipEffx = self.padding + (rect.height - self.shipEffBk.GetWidth())/2
        self.shipEffy = (rect.height - self.shipEffBk.GetHeight())/2

        self.shipEffx = self.shipEffx - self.animCount

        self.shipBmpx = self.padding + (rect.height - self.shipBmp.GetWidth()) / 2
        self.shipBmpy = (rect.height - self.shipBmp.GetHeight()) / 2

        self.shipBmpx= self.shipBmpx - self.animCount

        self.raceBmpx = self.shipEffx + self.shipEffBk.GetWidth() + self.padding
        self.raceBmpy = (rect.height - self.raceBmp.GetHeight())/2

        self.textStartx = self.raceBmpx + self.raceBmp.GetWidth() + self.padding

        self.shipNamey = (rect.height - self.shipBmp.GetHeight()) / 2

        shipName, fittings = self.shipFittingInfo

        mdc.SetFont(self.fontBig)
        wtext, htext = mdc.GetTextExtent(shipName)

        self.fittingsy = self.shipNamey + htext

        mdc.SetFont(self.fontSmall)

        wlabel,hlabel = mdc.GetTextExtent(self.toolbar.hoverLabel)

        self.thoverx = self.toolbarx - self.padding - wlabel
        self.thovery = (rect.height - hlabel)/2
        self.thoverw = wlabel

    def DrawItem(self, mdc):
        rect = self.GetRect()

        windowColor = wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW)
        textColor = colorUtils.GetSuitableColor(windowColor, 1)

        mdc.SetTextForeground(textColor)

        self.UpdateElementsPos(mdc)

        self.toolbar.SetPosition((self.toolbarx, self.toolbary))

        mdc.DrawBitmap(self.shipEffBk, self.shipEffx, self.shipEffy, 0)

        mdc.DrawBitmap(self.shipBmp, self.shipBmpx, self.shipBmpy, 0)

        mdc.DrawBitmap(self.raceBmp,self.raceBmpx, self.raceBmpy)

        shipName, fittings = self.shipFittingInfo

        if fittings <1:
            fformat = "No fits"
        else:
            if fittings == 1:
                fformat = "%d fit"
            else:
                fformat = "%d fits"

        mdc.SetFont(self.fontNormal)
        mdc.DrawText(fformat %fittings if fittings >0 else fformat, self.textStartx, self.fittingsy)

        mdc.SetFont(self.fontSmall)
        mdc.DrawText(self.toolbar.hoverLabel, self.thoverx, self.thovery)

        mdc.SetFont(self.fontBig)

        psname = drawUtils.GetPartialText(mdc, shipName, self.toolbarx - self.textStartx - self.padding * 2 - self.thoverw)

        mdc.DrawText(psname, self.textStartx, self.shipNamey)

        if self.tcFitName.IsShown():
            self.AdjustControlSizePos(self.tcFitName, self.textStartx, self.toolbarx - self.editWidth - self.padding)

    def AdjustControlSizePos(self, editCtl, start, end):
        fnEditSize = editCtl.GetSize()
        wSize = self.GetSize()
        fnEditPosX = end
        fnEditPosY = (wSize.height - fnEditSize.height)/2
        if fnEditPosX < start:
            editCtl.SetSize((self.editWidth + fnEditPosX - start,-1))
            editCtl.SetPosition((start,fnEditPosY))
        else:
            editCtl.SetSize((self.editWidth,-1))
            editCtl.SetPosition((fnEditPosX,fnEditPosY))

class PFBitmapFrame(wx.Frame):
    def __init__ (self,parent, pos, bitmap):
        wx.Frame.__init__(self, parent, id = wx.ID_ANY, title = wx.EmptyString, pos = pos, size = wx.DefaultSize, style =
                                                               wx.NO_BORDER
                                                             | wx.FRAME_NO_TASKBAR
                                                             | wx.STAY_ON_TOP)
        img = bitmap.ConvertToImage()
        img = img.ConvertToGreyscale()
        bitmap = wx.BitmapFromImage(img)
        self.bitmap = bitmap
        self.SetSize((bitmap.GetWidth(), bitmap.GetHeight()))
        self.Bind(wx.EVT_PAINT,self.OnWindowPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnWindowEraseBk)
        self.Bind(wx.EVT_TIMER, self.OnTimer)

        self.timer = wx.Timer(self,wx.ID_ANY)
        self.direction = 1
        self.transp = 0
        self.SetSize((bitmap.GetWidth(),bitmap.GetHeight()))

        self.SetTransparent(0)
        self.Refresh()

    def OnTimer(self, event):
        self.transp += 20*self.direction
        if self.transp > 200:
            self.transp = 200
            self.timer.Stop()
        if self.transp < 0:
            self.transp = 0
            self.timer.Stop()
            wx.Frame.Show(self,False)
            self.Destroy()
            return
        self.SetTransparent(self.transp)

    def Show(self, showWnd = True):
        if showWnd:
            wx.Frame.Show(self, showWnd)
            self.Parent.SetFocus()
            self.direction = 1
            self.timer.Start(5)
        else:
            self.direction = -1
            self.timer.Start(5)

    def SetRoundShape(self, event=None):
        w, h = self.GetSizeTuple()
        self.SetShape(GetRoundShape( w,h, 5 ) )
        self.SetTransparent(0)


    def OnWindowEraseBk(self,event):
        pass

    def OnWindowPaint(self,event):
        rect = self.GetRect()
        canvas = wx.EmptyBitmap(rect.width, rect.height)
        mdc = wx.BufferedPaintDC(self)
        mdc.SelectObject(canvas)
        mdc.DrawBitmap(self.bitmap, 0, 0)
        mdc.SetPen( wx.Pen("#000000", width = 1 ) )
        mdc.SetBrush( wx.TRANSPARENT_BRUSH )
        mdc.DrawRectangle( 0,0,rect.width,rect.height)


def GetRoundBitmap( w, h, r ):
    maskColor = wx.Color(0,0,0)
    shownColor = wx.Color(5,5,5)
    b = wx.EmptyBitmap(w,h)
    dc = wx.MemoryDC(b)
    dc.SetBrush(wx.Brush(maskColor))
    dc.DrawRectangle(0,0,w,h)
    dc.SetBrush(wx.Brush(shownColor))
    dc.SetPen(wx.Pen(shownColor))
    dc.DrawRoundedRectangle(0,0,w,h,r)
    dc.SelectObject(wx.NullBitmap)
    b.SetMaskColour(maskColor)
    return b

def GetRoundShape( w, h, r ):
    return wx.RegionFromBitmap( GetRoundBitmap(w,h,r) )


class FitItem(SBItem):
    def __init__(self, parent, fitID=None, shipFittingInfo=("Test", "cnc's avatar", 0 ), shipID = None, itemData=None,
                 id=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=(0, 40), style=0):
        SBItem.__init__(self,parent,size = size)

        self.mainFrame = gui.mainFrame.MainFrame.getInstance()

        self._itemData = itemData

        self.fitID = fitID

        self.shipID = shipID

        self.shipBrowser = self.Parent.Parent

        self.shipBmp = None

        self.deleted = False

        if shipID:
            self.shipBmp = bitmapLoader.getBitmap(str(shipID),"ships")

        if not self.shipBmp:
            self.shipBmp = bitmapLoader.getBitmap("ship_no_image_big","icons")

        self.shipFittingInfo = shipFittingInfo
        self.shipName, self.fitName, self.timestamp = shipFittingInfo

        self.copyBmp = bitmapLoader.getBitmap("fit_add_small", "icons")
        self.renameBmp = bitmapLoader.getBitmap("fit_rename_small", "icons")
        self.deleteBmp = bitmapLoader.getBitmap("fit_delete_small","icons")

        self.shipEffBk = bitmapLoader.getBitmap("fshipbk_big","icons")

        self.dragTLFBmp = None

        self.bkBitmap = None

        self.padding = 4
        self.editWidth = 150

        self.dragging = False
        self.dragged = False
        self.dragMotionTrail = 5
        self.dragMotionTrigger = self.dragMotionTrail
        self.dragWindow = None

        self.fontBig = wx.FontFromPixelSize((0,15),wx.SWISS, wx.NORMAL, wx.BOLD, False)
        self.fontNormal = wx.FontFromPixelSize((0,14),wx.SWISS, wx.NORMAL, wx.NORMAL, False)
        self.fontSmall = wx.FontFromPixelSize((0,12),wx.SWISS, wx.NORMAL, wx.NORMAL, False)

        self.toolbar.AddButton(self.copyBmp,"Copy", self.copyBtnCB)
        self.toolbar.AddButton(self.renameBmp,"Rename", self.renameBtnCB)
        self.toolbar.AddButton(self.deleteBmp, "Delete", self.deleteBtnCB)

        self.tcFitName = wx.TextCtrl(self, wx.ID_ANY, "%s" % self.fitName, wx.DefaultPosition, (self.editWidth,-1), wx.TE_PROCESS_ENTER)

        if self.shipBrowser.fitIDMustEditName != self.fitID:
            self.tcFitName.Show(False)
        else:
            self.tcFitName.SetFocus()
            self.tcFitName.SelectAll()

        self.tcFitName.Bind(wx.EVT_TEXT_ENTER, self.renameFit)
        self.tcFitName.Bind(wx.EVT_KILL_FOCUS, self.editLostFocus)
        self.tcFitName.Bind(wx.EVT_KEY_DOWN, self.editCheckEsc)

        self.selectedDelta = 0

        self.animTimerId = wx.NewId()
        self.animCount = 100
        self.animTimer = wx.Timer(self, self.animTimerId)
        self.animStep = 0
        self.animPeriod = 10
        self.animDuration = 100

        self.Bind(wx.EVT_TIMER, self.OnTimer)

        if self.shipBrowser.GetActiveStage() != 4 and self.shipBrowser.GetLastStage() !=3:
            self.animTimer.Start(self.animPeriod)
        else:
            self.animCount = 0

        self.selTimerID = wx.NewId()

        self.selTimer = wx.Timer(self,self.selTimerID)
        self.selTimer.Start(100)

    def OnTimer(self, event):

        if self.selTimerID == event.GetId():
            ctimestamp = time.time()
            interval = 10
            if ctimestamp < self.timestamp + interval:
                delta = (ctimestamp - self.timestamp) / interval
                self.selectedDelta = self.CalculateDelta(0x0,0x66,delta)
                self.Refresh()
            else:
                self.selectedDelta = 0x66
                self.selTimer.Stop()

        if self.animTimerId == event.GetId():
            step = self.OUT_QUAD(self.animStep, 0, 10, self.animDuration)
            self.animCount = 10 - step
            self.animStep += self.animPeriod
            if self.animStep > self.animDuration or self.animCount < 0 :
                self.animCount = 0
                self.animTimer.Stop()
            self.Refresh()

    def CalculateDelta(self, start, end, delta):
        return start + (end-start)*delta

    def OUT_QUAD (self, t, b, c, d):
        t=float(t)
        b=float(b)
        c=float(c)
        d=float(d)

        t/=d

        return -c *(t)*(t-2) + b

    def editLostFocus(self, event):
        self.tcFitName.Show(False)
        self.Refresh()

    def editCheckEsc(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.tcFitName.Show(False)
        else:
            event.Skip()

    def copyBtnCB(self):
        self.copyFit()

    def copyFit(self, event=None):
        sFit = service.Fit.getInstance()
        fitID = sFit.copyFit(self.fitID)
        self.shipBrowser.fitIDMustEditName = fitID
        wx.PostEvent(self.shipBrowser,Stage3Selected(shipID=self.shipID, back=True))
        wx.PostEvent(self.mainFrame, FitSelected(fitID=fitID))

    def renameBtnCB(self):
        if self.tcFitName.IsShown():
            self.tcFitName.Show(False)
            self.renameFit()
        else:
            self.tcFitName.SetValue(self.fitName)
            self.tcFitName.Show()

            self.tcFitName.SetFocus()
            self.tcFitName.SelectAll()

            self.Refresh()

    def renameFit(self, event=None):
        sFit = service.Fit.getInstance()
        self.tcFitName.Show(False)
        self.editWasShown = 0
        fitName = self.tcFitName.GetValue()
        if fitName:
            self.fitName = fitName
            sFit.renameFit(self.fitID, self.fitName)
            wx.PostEvent(self.mainFrame, FitRenamed(fitID=self.fitID))
            self.Refresh()
        else:
            self.tcFitName.SetValue(self.fitName)

    def deleteBtnCB(self):
        self.deleteFit()

    def deleteFit(self, event=None):
        if self.deleted:
            return
        else:
            self.deleted = True

        sFit = service.Fit.getInstance()

        sFit.deleteFit(self.fitID)

        if self.shipBrowser.GetActiveStage() == 4:
            wx.PostEvent(self.shipBrowser,SearchSelected(text=self.shipBrowser.hpane.lastSearch,back=True))
        else:
            wx.PostEvent(self.shipBrowser,Stage3Selected(shipID=self.shipID, back=True))

        wx.PostEvent(self.mainFrame, FitRemoved(fitID=self.fitID))

    def MouseLeftUp(self, event):

        if self.dragging and self.dragged:
            self.dragging = False
            self.dragged = False
            if self.HasCapture():
                self.ReleaseMouse()
            self.dragWindow.Show(False)
            self.dragWindow = None

            targetWnd = wx.FindWindowAtPointer()

            if not targetWnd:
                return

            wnd = targetWnd
            while wnd is not None:
                handler = getattr(wnd, "handleDrag", None)
                if handler:
                    handler("fit", self.fitID)
                    break
                else:
                    wnd = wnd.Parent
            event.Skip()
            return

        if self.dragging:
            self.dragging = False

        if self.tcFitName.IsShown():
            self.tcFitName.Show(False)
            self.Refresh()
        else:
            activeFitID = self.mainFrame.getActiveFit()
            if activeFitID != self.fitID:
                self.selectFit()

    def MouseLeftDown(self, event):
        self.dragging = True

    def MouseMove(self, event):
        pos = self.ClientToScreen(event.GetPosition())
        if self.dragging:
            if not self.dragged:
                if self.dragMotionTrigger < 0:
                    self.CaptureMouse()
                    self.dragWindow = PFBitmapFrame(self, pos, self.dragTLFBmp)
                    self.dragWindow.Show()
                    self.dragged = True
                    self.dragMotionTrigger = self.dragMotionTrail
                else:
                    self.dragMotionTrigger -= 1
            if self.dragWindow:
                pos.x += 3
                pos.y += 3
                self.dragWindow.SetPosition(pos)
            return

    def selectFit(self, event=None):
        wx.PostEvent(self.mainFrame, FitSelected(fitID=self.fitID))
        self.Parent.RefreshList(True)

    def UpdateElementsPos(self, mdc):
        rect = self.GetRect()

        self.toolbarx = rect.width - self.toolbar.GetWidth() - self.padding
        self.toolbary = (rect.height - self.toolbar.GetHeight()) / 2

        self.toolbarx = self.toolbarx + self.animCount

        self.shipEffx = self.padding + (rect.height - self.shipEffBk.GetWidth())/2
        self.shipEffy = (rect.height - self.shipEffBk.GetHeight())/2

        self.shipEffx = self.shipEffx - self.animCount

        self.shipBmpx = self.padding + (rect.height - self.shipBmp.GetWidth()) / 2
        self.shipBmpy = (rect.height - self.shipBmp.GetHeight()) / 2

        self.shipBmpx= self.shipBmpx - self.animCount

        self.textStartx = self.shipEffx + self.shipEffBk.GetWidth() + self.padding

        self.fitNamey = (rect.height - self.shipBmp.GetHeight()) / 2

        mdc.SetFont(self.fontBig)
        wtext, htext = mdc.GetTextExtent(self.fitName)

        self.timestampy = self.fitNamey + htext

        mdc.SetFont(self.fontSmall)

        wlabel,hlabel = mdc.GetTextExtent(self.toolbar.hoverLabel)

        self.thoverx = self.toolbarx - self.padding - wlabel
        self.thovery = (rect.height - hlabel)/2
        self.thoverw = wlabel

    def DrawItem(self, mdc):
        rect = self.GetRect()

        windowColor = wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW)
        textColor = colorUtils.GetSuitableColor(windowColor, 1)

        mdc.SetTextForeground(textColor)

        self.UpdateElementsPos(mdc)

        self.toolbar.SetPosition((self.toolbarx, self.toolbary))

        mdc.DrawBitmap(self.shipEffBk, self.shipEffx, self.shipEffy, 0)

        mdc.DrawBitmap(self.shipBmp, self.shipBmpx, self.shipBmpy, 0)

        shipName, fittings, timestamp = self.shipFittingInfo

        mdc.SetFont(self.fontNormal)

        fitDate = time.localtime(self.timestamp)
        fitLocalDate = "%02d/%02d %02d:%02d" % (fitDate[1], fitDate[2], fitDate[3], fitDate[4])

        mdc.DrawText(fitLocalDate, self.textStartx, self.timestampy)

        mdc.SetFont(self.fontSmall)
        mdc.DrawText(self.toolbar.hoverLabel, self.thoverx, self.thovery)

        mdc.SetFont(self.fontBig)

        psname = drawUtils.GetPartialText(mdc, self.fitName, self.toolbarx - self.textStartx - self.padding * 2 - self.thoverw)

        mdc.DrawText(psname, self.textStartx, self.fitNamey)

        if self.tcFitName.IsShown():
            self.AdjustControlSizePos(self.tcFitName, self.textStartx, self.toolbarx - self.editWidth - self.padding)

        tdc = wx.MemoryDC()
        self.dragTLFBmp = wx.EmptyBitmap((self.toolbarx if self.toolbarx < 200 else 200), rect.height)
        tdc.SelectObject(self.dragTLFBmp)
        tdc.Blit(0, 0, (self.toolbarx if self.toolbarx < 200 else 200), rect.height, mdc, 0, 0, wx.COPY)
        tdc.SelectObject(wx.NullBitmap)

    def AdjustControlSizePos(self, editCtl, start, end):
        fnEditSize = editCtl.GetSize()
        wSize = self.GetSize()
        fnEditPosX = end
        fnEditPosY = (wSize.height - fnEditSize.height)/2
        if fnEditPosX < start:
            editCtl.SetSize((self.editWidth + fnEditPosX - start,-1))
            editCtl.SetPosition((start,fnEditPosY))
        else:
            editCtl.SetSize((self.editWidth,-1))
            editCtl.SetPosition((fnEditPosX,fnEditPosY))

    def GetState(self):
        activeFitID = self.mainFrame.getActiveFit()

        if self.highlighted and not activeFitID == self.fitID:
            state = SB_ITEM_HIGHLIGHTED

        else:
            if activeFitID == self.fitID:
                if self.highlighted:
                    state = SB_ITEM_SELECTED  | SB_ITEM_HIGHLIGHTED
                else:
                    state = SB_ITEM_SELECTED
            else:
                state = SB_ITEM_NORMAL
        return state

    def RenderBackground(self):
        rect = self.GetRect()

        windowColor = wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW)

        activeFitID = self.mainFrame.getActiveFit()

        state = self.GetState()

        sFactor = 0.2
        mFactor = None
        eFactor = 0

        if state == SB_ITEM_HIGHLIGHTED:
            mFactor = 0.55

        elif state == SB_ITEM_SELECTED  | SB_ITEM_HIGHLIGHTED:
            eFactor = 0.3
        elif state == SB_ITEM_SELECTED:
            eFactor = (0x33 - self.selectedDelta)/100
        else:
            sFactor = 0

        if self.bkBitmap:
            if self.bkBitmap.eFactor == eFactor and self.bkBitmap.sFactor == sFactor and self.bkBitmap.mFactor == mFactor \
             and rect.width == self.bkBitmap.GetWidth() and rect.height == self.bkBitmap.GetHeight() :
                return
            else:
                del self.bkBitmap

        self.bkBitmap = drawUtils.RenderGradientBar(windowColor, rect.width, rect.height, sFactor, eFactor, mFactor)
        self.bkBitmap.state = state
        self.bkBitmap.sFactor = sFactor
        self.bkBitmap.eFactor = eFactor
        self.bkBitmap.mFactor = mFactor

