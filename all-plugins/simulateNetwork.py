'''
Network Simulation Plugin
'''

from rkviewer_plugins import exportSBML
import wx
import wx.lib.newevent
from rkviewer.plugin.classes import PluginMetadata, WindowedPlugin, PluginCategory
from rkviewer.plugin import api
from rkviewer.plugin.api import Node, Vec2, Reaction, Color
from rkviewer.canvas.geometry import Rect
import os
from libsbml import *
import tellurium as te
import roadrunner
import simplesbml 
import time
import numpy as np
import re

from rkviewer.events import bind_handler, unbind_handler, DidPaintCanvasEvent, DidNewNetworkEvent

class SimulateModel(WindowedPlugin): 
    metadata = PluginMetadata(
        name='Simulate Model',
        author='Claire Samuels',
        version='0.0.2',
        short_desc='Simulate a reaction network.',
        long_desc='Simulate a reaction network using roadrunner and visualize the results.',
        category=PluginCategory.ANALYSIS
    )
    def create_window(self, dialog):
        ''' 
          Create a window to start reaction
          Args:
              self
              dialog
        '''
        self.dialog = dialog
        self.window = wx.ScrolledWindow(dialog, size=(350, 550))
        self.window.SetScrollbars(1,1,1,1)
        self.vsizer = wx.BoxSizer(wx.VERTICAL)

        # need to load in current model as sbml to be able to set initial concentrations/values
        # requires exportSBML version 0.3.5 or later 
        def version_err_window():
            self.window = wx.Panel(dialog, pos=(5,100), size=(300, 320))
            txt = wx.StaticText(self.window, -1, "SimulateReaction requires ExportSBML version 0.3.5 or later!", (10,10))
            txt.Wrap(250)
            return self.window

        v = exportSBML.ExportSBML.metadata.version.split(".")
        exportSBMLvers = 0
        min_version = [0,3,5]
        for i in range(3):
            if int(v[i]) < min_version[i]:
                return version_err_window()
            elif int(v[i]) > min_version[i]:
                break
       
        sbml = exportSBML.ExportSBML.NetworkToSBML(self)
        
        self.model = simplesbml.loadSBMLStr(sbml)

        self.main_sizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.grid = wx.GridBagSizer(vgap=10, hgap=5)
        self.sim_grid = wx.GridBagSizer(vgap=5, hgap=15)
        
        # simulation
        self.sim_grid.Add(wx.StaticText(self.window, -1, label="Start"), pos=(1,1))
        self.sim_start_input = wx.TextCtrl(self.window, -1, value="0", size=(40,20))
        self.sim_grid.Add(self.sim_start_input, pos=(1,2))
        self.sim_grid.Add(wx.StaticText(self.window, -1, label="End"), pos=(2,1))
        self.sim_end_input = wx.TextCtrl(self.window, -1, value="20", size=(40,20))
        self.sim_grid.Add(self.sim_end_input, pos=(2,2))
        self.sim_grid.Add(wx.StaticText(self.window, -1, label="Seconds per Point"), pos=(2,3))
        self.sim_step_time = wx.TextCtrl(self.window, -1, value="1.0", size=(40,20))
        self.sim_grid.Add(self.sim_step_time, pos=(2,4))
        self.go_btn = wx.Button(self.window, -1, "Simulate", (5,6))
        self.go_btn.Bind(wx.EVT_BUTTON, self.go)
        self.sim_grid.Add(self.go_btn, pos=(3,4))
        self.run_cont = False
        self.is_continuous = wx.CheckBox(self.window, label="Continuous")
        self.is_continuous.Bind(wx.EVT_CHECKBOX, self.continuous_mode)
        self.sim_grid.Add(self.is_continuous, pos=(3,3))
        self.stop_btn = wx.Button(self.window, label="Stop")
        self.stop_btn.Bind(wx.EVT_BUTTON, self.stop_sim)
        self.sim_grid.Add(self.stop_btn, pos=(4,4))
        self.stop_btn.Hide()
        self.main_sizer.Add(self.sim_grid)
        self.main_sizer.AddSpacer(5)

        self.species_iv_tc = []
        self.param_iv_tc = []
        
        self.grid.Add(wx.StaticText(self.window, -1, label="Species Initial Values"), pos=(0,1), span=(1,2))
        row = 1
        species = self.model.getListOfAllSpecies()
        for sidx, s in enumerate(species):
            self.grid.Add(wx.StaticText(self.window, -1, label=s, size=(40,20)), pos=(row,1))
            sval = 0.0
            if self.model.isSpeciesValueSet(s):
                sval = self.model.getSpeciesInitialConcentration(s)
            tc_slider = SliderWithText(self.window, init_val=sval, name=s)
            self.species_iv_tc.append(tc_slider)
            self.grid.Add(tc_slider, pos=(row, 2), span=(1,2))
            row += 1
        
        self.grid.Add(wx.StaticText(self.window, -1, label="Parameter Initial Values"), pos=(row,1), span=(1,2))
        row +=1
        params = self.model.getListOfParameterIds()
        for pidx, p in enumerate(params):
            self.grid.Add(wx.StaticText(self.window, -1, label=p, size=(40,20)), pos=(row,1))
            pval = 1.0
            if self.model.isParameterValueSet(p):
                pval = self.model.getParameterValue(p) # TODO kind of an issue that it can only do integers
            tc_slider = SliderWithText(self.window, init_val=pval, name=p)
            self.param_iv_tc.append(tc_slider)
            self.grid.Add(tc_slider, pos=(row, 2), span=(1,2))
            row += 1

        self.initial_value_tc = self.species_iv_tc + self.param_iv_tc

        # for painting and updating model
        self.nodeinfo = dict()
        # maps ids (names) to indices and display text. points is the quantity at all the time points
        for n in api.get_nodes(0):
            self.nodeinfo[n.id] = {"index": n.index, "points": [], "floating": n.floating_node}
            if n.floating_node:
                self.nodeinfo[n.id]["points"] = [n.concentration]
            # TODO do first point here by pulling th concentration from the node
        self.reacinfo = dict()
        for r in api.get_reactions(0):
            self.reacinfo[r.id] = {"index": r.index, "rate_law": ""}

        self.main_sizer.Add(self.grid)

        self.window.SetSizer(self.main_sizer)
        return self.window

    def continuous_mode(self, evt):
        ''' Handler for is_continuous button
        '''
        if self.is_continuous.GetValue():
            self.sim_end_input.Disable()
        else:
            self.sim_end_input.Enable()

    def stop_sim(self, evt):
        '''
        Stops the simulation
        '''
        #self.chose_stop_sim = True
        self.stop_btn.Hide()
        self.go_btn.Enable()
        self.timer.Stop()
        self.remove(any)
        donemsg = wx.MessageBox("Done.", "Simulate Network", wx.OK | wx.CANCEL)
        if donemsg == wx.OK:
            self.update_network(0)

    def go(self, evt):

        # handler for go button

        # validate input
        for sp in self.initial_value_tc:
            name = sp.GetName()
            if sp.IsModified():
                # check that input is valid
                inpt = sp.GetValue()
                try:
                    f_inpt = float(inpt) # change to float, then change back...
                except ValueError:
                    wx.MessageBox("Invalid input for {}".format(name), "Message", wx.OK | wx.ICON_INFORMATION)
                    return
                self.model.addInitialAssignment(name, str(f_inpt))
        # update rate laws
        for r in self.model.getListOfReactionIds():
            self.reacinfo[r]["rate_law"] = self.model.getRateLaw(r) # TODO i really think this process is redundant. do i even need to have this dictionary?

        self.go_btn.Disable()
        self.stop_btn.Show()
        #self.chose_stop_sim = False
        
        ant = te.sbmlToAntimony(self.model)
        self.r = te.loada(ant)
        self.step_time = float(self.sim_step_time.GetValue())
        self.time = self.r.oneStep(0, self.step_time)
        self.update_node_info()
        self.timer = wx.Timer(owner=self.window)
        self.window.Bind(wx.EVT_TIMER, self.do_one_step, self.timer)
        self.end_time = None
        if not self.is_continuous.GetValue():
            self.end_time = float(self.sim_end_input.GetValue())
        self.paint_id = bind_handler(DidPaintCanvasEvent, self.on_paint)
        bind_handler(DidNewNetworkEvent, self.remove)

        self.timer.Start(1000 * float(self.sim_step_time.GetValue()))

    def do_one_step(self, evt):
        '''
        Handler for timer event
        '''
        self.time = self.r.oneStep(self.time, self.step_time)
        self.update_node_info()
        api.update_canvas()
        if self.end_time and self.time >= self.end_time:
            self.stop_sim(evt)

    def update_node_info(self): 
        ''' 
        Update concentrations to be displayed by on_paint
        '''
        net_index = 0
        sim = self.r.getFloatingSpeciesConcentrationsNamedArray()
        # want the final value of the concentration for the nodes
        # get the number of columns
        for i in range(len(sim.colnames)):
            col = sim[:,i]
            node_id = sim.colnames[i]
            if node_id in self.nodeinfo: # TODO this should always be true
                self.nodeinfo[node_id]["points"].extend(col)

    def update_network(self, net_index):
        '''
        Update model node concentrations and reaction rate laws
        '''
        with api.group_action():
            for node_id in self.nodeinfo:
                idx = self.nodeinfo[node_id]["index"]
                #if len(self.nodeinfo[node_id]["points"]) > 0:
                if self.nodeinfo[node_id]["floating"]:
                    final_conc = self.nodeinfo[node_id]["points"][-1]
                    api.update_node(net_index, idx, concentration=final_conc)
            for reac_id in self.reacinfo:
                idx = self.reacinfo[reac_id]["index"]
                api.update_reaction(net_index, idx, ratelaw=self.reacinfo[reac_id]["rate_law"])
                
        # remake the model
        sbml = exportSBML.ExportSBML.NetworkToSBML(self)
        self.model = simplesbml.loadSBMLStr(sbml)
        # update values in text controls
        for s in self.species_iv_tc:
            s.SetValue(api.get_node_by_index(0, self.nodeinfo[s.GetName()]["index"]).concentration)
        for p in self.param_iv_tc:
            p._is_modified = True # TODO fix

    def remove(self, evt):
        try:
            unbind_handler(self.paint_id) # TODO this should happen in events.py, not here
        except KeyError:
            pass


    def on_paint(self, evt):


        # paint node concentrations next to the nodes 
        gc = evt.gc
        # TODO have an option between numbers and shapes
        '''
        font = wx.Font(wx.FontInfo(10))
        gc.SetFont(font, wx.Colour(0,0,0))
        pen1 = gc.CreatePen(wx.GraphicsPenInfo(wx.Colour(0,0,150)))
        gc.SetPen(pen1)

        net_index = 0
        for node_id in self.nodeinfo:
            info = self.nodeinfo[node_id]
            node = api.get_node_by_index(net_index, info["index"])
            gc.DrawText(str(round(info["points"][self.current_point], 3)), node.position.x - 30, node.position.y + 50)
        '''
        # create pens
        pen1 = gc.CreatePen(wx.GraphicsPenInfo(wx.Colour(150,150,150)))
        brush1 = wx.Brush(wx.Colour(150,150,150), style = wx.BRUSHSTYLE_SOLID)
        pen2 = gc.CreatePen(wx.GraphicsPenInfo(wx.Colour(0,250,70)))
        brush2 = wx.Brush(wx.Colour(0,250,70), style = wx.BRUSHSTYLE_SOLID)
        yellowpen = gc.CreatePen(wx.GraphicsPenInfo(wx.Colour(250,230,0)))
        yellowbrush = wx.Brush(wx.Colour(250,230,0), style = wx.BRUSHSTYLE_SOLID)
        # blue brush
        bg_w = 10
        bg_h = 50
        bg_x = 20 
        bg_y = 20
        max_conc = 20 # this is pretty arbitraty, could change

        def rect_from_conc(concentration):
            '''# Calculate dimensions of bar for graph
            '''
            # 4 px buffer
            w = bg_w - 8
            h = bg_h - 8
            x = bg_x - 4
            y = bg_y - 4

            ratio =  (concentration)/max_conc
            adj_h = round(h * ratio)
            adj_y = y + adj_h - h # maybe switch adj_h and h

            return Rect(Vec2(x,adj_y), Vec2(w,adj_h))
        
        net_index = 0
        for node_id in self.nodeinfo:
            info = self.nodeinfo[node_id]
            node = api.get_node_by_index(net_index, info["index"])
            #if len(info["points"]) > 0:
            if info["floating"]:
                # draw background
                gc.SetPen(pen1)
                gc.SetBrush(brush1)
                gc.DrawRoundedRectangle(node.position.x - bg_x, node.position.y - bg_y, bg_w, bg_h, 2)
                conc = info["points"][-1]
                # draw dynamic bar
                if conc <= max_conc:
                    gc.SetBrush(brush2)
                    gc.SetPen(pen2)
                    bar = rect_from_conc(conc)
                else:
                    gc.SetBrush(yellowbrush)
                    gc.SetPen(yellowpen)
                    bar = rect_from_conc(max_conc)
                gc.DrawRoundedRectangle(node.position.x - bar.position.x, node.position.y - bar.position.y, bar.size.x, bar.size.y, 0)
            '''
            else: # boundary node
                # draw background
                gc.SetPen(pen1)
                gc.SetBrush(brush1)
                gc.DrawRoundedRectangle(node.position.x - bg_x, node.position.y - bg_y, bg_w, bg_h, 2)
                conc = info["points"][-1]
                # draw dynamic bar
                if conc <= max_conc:
                    gc.SetBrush(brush2)
                    gc.SetPen(pen2)
                    bar = rect_from_conc(conc)
                else:
                    gc.SetBrush(yellowbrush)
                    gc.SetPen(yellowpen)
                    bar = rect_from_conc(max_conc)
                gc.DrawRoundedRectangle(node.position.x - bar.position.x, node.position.y - bar.position.y, bar.size.x, bar.size.y, 0)
            '''


class SliderWithText(wx.Panel):
    def __init__(self, parent, init_val=0.0, name=None):
        wx.Panel.__init__(self, parent, size=(200,40))
        self.name=name
        self.slider = wx.Slider(self, -1, size=(150,20), maxValue=100)
        self.tc = wx.TextCtrl(self, -1, size=(30,20))
        self.sizer = wx.GridBagSizer()
        self.SetValue(init_val)

        self.sizer.Add(self.tc, pos=(0,0), border=5)
        self.sizer.Add(self.slider, pos=(0,1), border=20, flag=wx.RIGHT)
        self.labels_sizer = wx.BoxSizer()
        self.labels_sizer.Add(wx.StaticText(self, -1, "0", size=(10,15)), border=10, flag=wx.LEFT)
        self.labels_sizer.AddSpacer(115)
        self.labels_sizer.Add(wx.StaticText(self, -1, "20", size=(15,15)))
        self.sizer.Add(self.labels_sizer, pos=(1,1))
        self.SetSizer(self.sizer)
        
        self._is_modified = False
        self.slider.Bind(wx.EVT_SLIDER, self._on_slider)
        self.tc.Bind(wx.EVT_TEXT, self._on_text)

    def SetValue(self, value):
        self.tc.SetValue(str(value))
        self._set_slider_val(value)
        self._is_modified = True

    def GetValue(self):
        return float(self.tc.GetValue())

    def GetName(self):
        return self.name

    def IsModified(self):
        return self._is_modified

    def _on_slider(self, evt):
        self.tc.SetValue(str(self._get_slider_val()))
        self._is_modified=True
    def _on_text(self, evt):

        try:
            val = float(self.tc.GetValue())
        except ValueError as err: # TODO will need to do something different than this but dont remember what
            print(err)
            return
        self._set_slider_val(val)
        self._is_modified=True
        
    def _get_slider_val(self):
        return self.slider.GetValue()/5

    def _set_slider_val(self, value):
        self.slider.Enable()
        if value <= 20 and value >= 0:
            self.slider.SetValue(round(value*5))
        else:
            self.slider.Disable()
