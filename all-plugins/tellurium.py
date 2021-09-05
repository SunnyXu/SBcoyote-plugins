'''
tellurium plugin
'''

from rkviewer_plugins import exportSBML
import wx
from rkviewer.plugin.classes import PluginMetadata, WindowedPlugin, PluginCategory
from rkviewer.plugin import api
from rkviewer.plugin.api import Node, Vec2, Reaction, Color
import os
from libsbml import *
import tellurium as te
import roadrunner
import simplesbml # TODO may not use
import time
import numpy as np
import re

from rkviewer.events import bind_handler, unbind_handler, DidPaintCanvasEvent, DidNewNetworkEvent

class SimulateModel(WindowedPlugin): 
    metadata = PluginMetadata(
        name='Simulate Model',
        author='Claire Samuels',
        version='0.0.1',
        short_desc='coming soon',
        long_desc='coming soon',
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
        self.window = wx.ScrolledWindow(dialog, pos=(5,100), size=(400, 400))
        self.window.SetScrollbars(1,1,1,1)
        self.vsizer = wx.BoxSizer(wx.VERTICAL) # TODO figure out how to use sizers

        # need to load in current model as sbml to be able to set levels of things
        # will use exportSBML, may have to change it a bit
        
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
        self.grid = wx.GridBagSizer(vgap=5, hgap=5)
        self.sim_grid = wx.GridBagSizer(vgap=5, hgap=15)

        # simulation
        self.sim_grid.Add(wx.StaticText(self.window, -1, label="Start"), pos=(1,1))
        self.sim_start_input = wx.TextCtrl(self.window, -1, value="0", size=(40,20))
        self.sim_grid.Add(self.sim_start_input, pos=(1,2))
        self.sim_grid.Add(wx.StaticText(self.window, -1, label="End"), pos=(2,1))
        self.sim_end_input = wx.TextCtrl(self.window, -1, value="20", size=(40,20))
        self.sim_grid.Add(self.sim_end_input, pos=(2,2))
        self.sim_grid.Add(wx.StaticText(self.window, -1, label="Points"), pos=(1,3))
        self.sim_points_input = wx.TextCtrl(self.window, -1, value="10", size=(40,20)) # TODO change default points and seconds per point
        self.sim_grid.Add(self.sim_points_input, pos=(1,4))
        self.sim_grid.Add(wx.StaticText(self.window, -1, label="Seconds per Point"), pos=(2,3))
        self.sim_step_time = wx.TextCtrl(self.window, -1, value="1.0", size=(40,20))
        self.sim_grid.Add(self.sim_step_time, pos=(2,4))
        self.go_btn = wx.Button(self.window, -1, "Simulate", (5,6))
        self.go_btn.Bind(wx.EVT_BUTTON, self.go)
        self.sim_grid.Add(self.go_btn, pos=(3,4))
        self.main_sizer.Add(self.sim_grid)
        self.main_sizer.AddSpacer(5)

        self.initial_value_tc = []
        
        # species initial concentrations
        self.values_labels = wx.BoxSizer()
        self.values_labels.AddSpacer(15)
        self.values_labels.Add(wx.StaticText(self.window, -1, label="Species Initial Values"))
        species = self.model.getListOfAllSpecies()
        for idx, s in enumerate(species):
            self.grid.Add(wx.StaticText(self.window, -1, label=s, size=(40,20)), pos=(idx,1))
            sval = "0.0"
            if self.model.isSpeciesValueSet(s):
                sval = str(self.model.getSpeciesInitialConcentration(s))
            tc = wx.TextCtrl(self.window, -1, value=sval, size=(60,20), name=s)
            self.initial_value_tc.append(tc)
            self.grid.Add(tc, pos=(idx,2))
                     
        # parameter values
        self.values_labels.AddSpacer(10)
        self.values_labels.Add(wx.StaticText(self.window, -1, label="Parameter Initial Values"))
        params = self.model.getListOfParameterIds()
        for idx, p in enumerate(params):
            self.grid.Add(wx.StaticText(self.window, -1, label=p, size=(40,20)), pos=(idx,4))
            pval = "1"
            if self.model.isParameterValueSet(p):
                pval = round(self.model.getParameterValue(p)) # TODO kind of an issue that it can only do integers
            #tc = wx.TextCtrl(self.window, -1, value=pval, size=(60,20), name=p)
            slider = wx.Slider(self.window, value=pval, maxValue=10, style=wx.SL_AUTOTICKS)
            self.initial_value_tc.append(slider)
            self.grid.Add(slider, pos=(idx,5))

        # for painting and updating model
        self.nodeinfo = dict()
        # maps ids (names) to indices and display text. points is the quantity at all the time points
        for n in api.get_nodes(0):
            self.nodeinfo[n.id] = {"index": n.index, "points": []}
        self.reacinfo = dict()
        for r in api.get_reactions(0):
            self.reacinfo[r.id] = {"index": r.index, "rate_law": ""}

        self.main_sizer.Add(self.values_labels)
        self.main_sizer.Add(self.grid)

        self.window.SetSizer(self.main_sizer)
        return self.window

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

        self.sim_points = int(self.sim_points_input.GetValue())
        ant = te.sbmlToAntimony(self.model)
        r = te.loada(ant)
        sim1 = r.simulate(start=int(self.sim_start_input.GetValue()), end=int(self.sim_end_input.GetValue()), points=self.sim_points)

        self.update_node_info(sim1)

        self.current_point = 0
        self.paint_id = bind_handler(DidPaintCanvasEvent, self.on_paint)
        bind_handler(DidNewNetworkEvent, self.remove)

        self.dialog.Close()

        # time simulation
        self.step_time = float(self.sim_step_time.GetValue()) # TODO error checking
        self.timer = wx.Timer(owner=self.window)
        self.window.Bind(wx.EVT_TIMER, self.update_current_point, self.timer)

        self.timer.Start(1000 * self.step_time)
    
    def update_current_point(self, evt):
        if self.current_point < self.sim_points - 1:
            self.current_point += 1
            api.update_canvas()
        else:
            self.timer.Stop()
            donemsg = wx.MessageBox("Done.", "Simulate Network", wx.OK | wx.CANCEL)
            if donemsg == wx.OK:
                self.update_network(0)
            self.remove(any)

    def update_node_info(self, sim): 
        ''' args:
        '''
        net_index = 0
        # want the final value of the concentration for the nodes
        # get the number of columns
        num_columns = len(sim.colnames)
        for i in range(1, len(sim.colnames)):
            col = sim[:,i]
            node_id = re.split('\[|\]', sim.colnames[i])[1] # TODO this relies on 'time' always being the first column
            if node_id in self.nodeinfo: # this should always be true
                self.nodeinfo[node_id]["points"] = col

    def update_network(self, net_index):
        # update the nodes
        with api.group_action():
            for node_id in self.nodeinfo:
                idx = self.nodeinfo[node_id]["index"]
                final_conc = self.nodeinfo[node_id]["points"][-1]
                api.update_node(net_index, idx, concentration=final_conc)
            for reac_id in self.reacinfo:
                idx = self.reacinfo[reac_id]["index"]
                api.update_reaction(net_index, idx, ratelaw=self.reacinfo[reac_id]["rate_law"])

    def remove(self, evt):
        try:
            unbind_handler(self.paint_id) # TODO this should happen in events.py, not here
        except KeyError:
            pass

    def on_paint(self, evt):
        # paint node concentrations next to the nodes 
        gc = evt.gc
        font = wx.Font(wx.FontInfo(10))
        gc.SetFont(font, wx.Colour(0,0,0))
        pen1 = gc.CreatePen(wx.GraphicsPenInfo(wx.Colour(0,0,150)))
        gc.SetPen(pen1)

        net_index = 0
        for node_id in self.nodeinfo:
            info = self.nodeinfo[node_id]
            node = api.get_node_by_index(net_index, info["index"])
            gc.DrawText(str(round(info["points"][self.current_point], 3)), node.position.x - 30, node.position.y + 50)
            
    # listbook page for species
    def species_page(self):
        page = wx.Panel(self.dialog)

        self.species_labels = wx.BoxSizer()
        self.species_labels.AddSpacer(15)
        self.species_labels.Add(wx.StaticText(self.window, -1, label="Species Initial Values"))
        species = self.model.getListOfAllSpecies()
        for idx, s in enumerate(species):
            self.grid.Add(wx.StaticText(self.window, -1, label=s, size=(40,20)), pos=(idx,1))
            sval = "0.0"
            if self.model.isSpeciesValueSet(s):
                sval = str(self.model.getSpeciesInitialConcentration(s))
            tc = wx.TextCtrl(self.window, -1, value=sval, size=(60,20), name=s)
            self.initial_value_tc.append(tc)
            self.grid.Add(tc, pos=(idx,2))
        


