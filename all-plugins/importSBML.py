"""
Import an SBML string from a file and visualize it to a network on canvas.
Version 0.02: Author: Jin Xu (2021)
"""


# pylint: disable=maybe-no-member

from ast import Num
from inspect import Parameter
from ntpath import join
from re import S
import wx
from wx.core import CENTER
from rkviewer.canvas.data import TEXT_POSITION_CHOICES, TextAlignment, TextPosition
from rkviewer.plugin.classes import PluginMetadata, WindowedPlugin, PluginCategory
from rkviewer.plugin import api
from rkviewer.plugin.api import Node, Vec2, Reaction, Color
import os
import simplesbml # does not have to import in the main.py too
from libsbml import *
import math
import random as _random

class IMPORTSBML(WindowedPlugin):
    metadata = PluginMetadata(
        name='ImportSBML',
        author='Jin Xu',
        version='0.5.0',
        short_desc='Import SBML.',
        long_desc='Import an SBML String from a file and visualize it as a network on canvas.',
        category=PluginCategory.ANALYSIS
    )

    def create_window(self, dialog):
        """
        Create a window to import SBML.
        Args:
            self
            dialog
        """
        self.window = wx.Panel(dialog, pos=(5,100), size=(300, 320))
        self.sbmlStr = ''
        show_btn = wx.Button(self.window, -1, 'Load', (5, 5))
        show_btn.Bind(wx.EVT_BUTTON, self.Show)

        copy_btn = wx.Button(self.window, -1, 'Copy To Clipboard', (83, 5))
        copy_btn.Bind(wx.EVT_BUTTON, self.Copy)

        visualize_btn = wx.Button(self.window, -1, 'Visualize', (205, 5))
        visualize_btn.Bind(wx.EVT_BUTTON, self.Visualize)

        wx.StaticText(self.window, -1, 'SBML string:', (5,30))
        self.SBMLText = wx.TextCtrl(self.window, -1, "", (10, 50), size=(260, 220), style=wx.TE_MULTILINE|wx.HSCROLL)
        self.SBMLText.SetInsertionPoint(0)

        return self.window

    def Show(self, evt):
        """
        Handler for the "Import" button.
        Open the SBML file and show it in the TextCtrl box.
        """

        self.dirname=""  #set directory name to blank
        dlg = wx.FileDialog(self.window, "Choose a file to open", self.dirname, wildcard="SBML files (*.xml)|*.xml", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) #open the dialog boxto open file
        if dlg.ShowModal() == wx.ID_OK:  #if positive button selected....
            self.filename = dlg.GetFilename()  #get the filename of the file
            self.dirname = dlg.GetDirectory()  #get the directory of where file is located
            f = open(os.path.join(self.dirname, self.filename), 'r')  #traverse the file directory and find filename in the OS
            self.sbmlStr = f.read()
            self.SBMLText.SetValue(f.read())  #open the file from location as read
            self.SBMLText.WriteText(self.sbmlStr)
            f.close
        dlg.Destroy()

    def Copy(self, evt):
        """
        Handler for the "Copy" button.
        Copy the SBML string to a clipboard.
        """
        self.dataObj = wx.TextDataObject()
        self.dataObj.SetText(self.SBMLText.GetValue())
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(self.dataObj)
            wx.TheClipboard.Close()
        else:
            wx.MessageBox("Unable to open the clipboard", "Error")

    def Visualize(self, evt):
        """
        Handler for the "Visualize" button.
        Visualize the SBML string to a network shown on the canvas.
        """  

        with wx.BusyCursor():
        #with wx.BusyInfo("Please wait, working..."):
            self.DisplayModel(self.sbmlStr, True, False)


    def DisplayModel(self, sbmlStr, showDialogues, useSeed):
        """
        Visualize an SBML string as a network shown on the canvas.
        Args:
          self
          document: SBMLDocument object created from the sbml string
          sbmlStr: sbml string to display
          showDialogues: if false, hides pop-up windows
          useSeed: if true, constant seed for random number generation used,
                   ensuring that different visualizations created from the same
                   file will always have the same layout
        """
        if useSeed:
          _random.seed(13)

        def hex_to_rgb(value):
            value = value.lstrip('#')
            return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))

        # if len(sbmlStr) == 0:
        #   if showDialogues:
        #     wx.MessageBox("Please import an SBML file.", "Message", wx.OK | wx.ICON_INFORMATION)
        # else:
        if len(sbmlStr) != 0:
            net_index = 0
            api.clear_network(net_index)
            comp_id_list = []
            comp_dimension_list = []
            comp_position_list = []
            spec_id_list = []
            specGlyph_id_list = []
            spec_specGlyph_id_list = []
            spec_dimension_list = []
            spec_position_list = []
            spec_text_alignment_list = []
            spec_text_position_list = []
            spec_concentration_list = []

            shapeIdx = 0

            #set the default values without render info:
            comp_fill_color = (158, 169, 255)
            comp_border_color = (0, 29, 255)
            comp_border_width = 2.0
            spec_fill_color = (255, 204, 153)
            spec_border_color = (255, 108, 9)
            spec_border_width = 2.0
            reaction_line_color = (129, 123, 255)
            reaction_line_width = 3.0
            #text_line_color = (0,0,0)
            #text_line_width = 1.

            ### from here for layout ###
            document = readSBMLFromString(sbmlStr)
            model_layout = document.getModel()
            mplugin = (model_layout.getPlugin("layout"))

            # Get the first Layout object via LayoutModelPlugin object.
            #
            # if mplugin is None:
            #     if showDialogues:
            #         wx.MessageBox("There is no layout information, so positions are randomly assigned.", "Message", wx.OK | wx.ICON_INFORMATION)
            # else:
            if mplugin is not None:
                layout = mplugin.getLayout(0)
                # if layout is None:
                #     if showDialogues:
                #         wx.MessageBox("There is no layout information, so positions are randomly assigned.", "Message", wx.OK | wx.ICON_INFORMATION)
                # else:
                if layout is not None:
                    numCompGlyphs = layout.getNumCompartmentGlyphs()
                    numSpecGlyphs = layout.getNumSpeciesGlyphs()
                    numReactionGlyphs = layout.getNumReactionGlyphs()

                    for i in range(numCompGlyphs):
                        compGlyph = layout.getCompartmentGlyph(i)
                        temp_id = compGlyph.getCompartmentId()
                        comp_id_list.append(temp_id)
                        boundingbox = compGlyph.getBoundingBox()
                        height = boundingbox.getHeight()
                        width = boundingbox.getWidth()
                        pos_x = boundingbox.getX()
                        pos_y = boundingbox.getY()
                        comp_dimension_list.append([width,height])
                        comp_position_list.append([pos_x,pos_y])

                    # for i in range(numSpecGlyphs):
                    #     specGlyph = layout.getSpeciesGlyph(i)
                    #     spec_id = specGlyph.getSpeciesId()
                    #     spec_id_list.append(spec_id)
                    #     boundingbox = specGlyph.getBoundingBox()
                    #     height = boundingbox.getHeight()
                    #     width = boundingbox.getWidth()
                    #     pos_x = boundingbox.getX()
                    #     pos_y = boundingbox.getY()
                    #     spec_dimension_list.append([width,height])
                    #     spec_position_list.append([pos_x,pos_y])

                    reaction_id_list = []
                    reaction_center_list = []
                    kinetics_list = []
                    rct_specGlyph_list = []
                    prd_specGlyph_list = []

                    for i in range(numReactionGlyphs):
                        reactionGlyph = layout.getReactionGlyph(i)
                        curve = reactionGlyph.getCurve()
                        listOfCurveSegments = curve.getListOfCurveSegments()
                        for j in range(len(listOfCurveSegments)):
                            center_x = curve.getCurveSegment(j).getStart().x()
                            center_y = curve.getCurveSegment(j).getStart().y()
                            reaction_center_list.append([center_x, center_y])
                        reaction_id = reactionGlyph.getReactionId()
                        reaction_id_list.append(reaction_id)
                        reaction = model_layout.getReaction(reaction_id)
                        kinetics = reaction.getKineticLaw().getFormula()
                        kinetics_list.append(kinetics)
                        numSpecRefGlyphs = reactionGlyph.getNumSpeciesReferenceGlyphs()

                        rct_specGlyph_temp_list = []
                        prd_specGlyph_temp_list = []


                        for j in range(numSpecRefGlyphs):
                            alignment_name = TextAlignment.CENTER
                            position_name = TextPosition.IN_NODE
                            specRefGlyph = reactionGlyph.getSpeciesReferenceGlyph(j)
                            #specRefGlyph_id = specRefGlyph.getSpeciesReferenceGlyphId()

                            # curve = specRefGlyph.getCurve()
                            # listOfCurveSegments = curve.getListOfCurveSegments()
                            # for k in range(len(listOfCurveSegments)):
                                #print(curve.getCurveSegment(k).getStart().x())
                                #print(curve.getCurveSegment(k).getEnd().y())
                                #print(curve.getCurveSegment(k).getBasePoint1) #no children
                                #print(curve.getCurveSegment(k).getBasePoint2)
                            role = specRefGlyph.getRoleString()
                            specGlyph_id = specRefGlyph.getSpeciesGlyphId()
                            specGlyph = layout.getSpeciesGlyph(specGlyph_id)
                            
                            for k in range(numSpecGlyphs):
                                textGlyph_temp = layout.getTextGlyph(k)
                                temp_specGlyph_id = textGlyph_temp.getOriginOfTextId()
                                if temp_specGlyph_id == specGlyph_id:
                                    textGlyph = textGlyph_temp

                            spec_id = specGlyph.getSpeciesId()
                            spec = model_layout.getSpecies(spec_id)
                            try:
                                concentration = spec.getInitialConcentration()
                            except:
                                concentration = 1.
                            spec_boundingbox = specGlyph.getBoundingBox()
                            height = spec_boundingbox.getHeight()
                            width = spec_boundingbox.getWidth()
                            pos_x = spec_boundingbox.getX()
                            pos_y = spec_boundingbox.getY()

                            try:
                                text_boundingbox = textGlyph.getBoundingBox()
                                text_pos_x = text_boundingbox.getX()
                                text_pos_y = text_boundingbox.getY()
                                if text_pos_x < pos_x:
                                    alignment_name = TextAlignment.LEFT
                                if text_pos_x > pos_x:
                                    alignment_name = TextAlignment.RIGHT  
                                if text_pos_y < pos_y:
                                    position_name = TextPosition.ABOVE
                                if text_pos_y > pos_y:
                                    position_name = TextPosition.BELOW
                                if text_pos_y == pos_y and text_pos_x != pos_x:
                                    position_name = TextPosition.NEXT_TO 
                            except:
                                pass   

                            if specGlyph_id not in specGlyph_id_list:
                                spec_id_list.append(spec_id)
                                specGlyph_id_list.append(specGlyph_id)
                                spec_specGlyph_id_list.append([spec_id,specGlyph_id])
                                spec_dimension_list.append([width,height])
                                spec_position_list.append([pos_x,pos_y])
                                spec_text_alignment_list.append(alignment_name)
                                spec_text_position_list.append(position_name)
                                spec_concentration_list.append(concentration)

                            if role == "substrate": #it is a rct
                                rct_specGlyph_temp_list.append(specGlyph_id)
                            elif role == "product": #it is a prd
                                prd_specGlyph_temp_list.append(specGlyph_id)

                        rct_specGlyph_list.append(rct_specGlyph_temp_list)
                        prd_specGlyph_list.append(prd_specGlyph_temp_list)


                    rPlugin = layout.getPlugin("render")
                    if (rPlugin != None and rPlugin.getNumLocalRenderInformationObjects() > 0):
                        #wx.MessageBox("The diversity of each graphical object is not shown.", "Message", wx.OK | wx.ICON_INFORMATION)
                        info = rPlugin.getRenderInformation(0)
                        color_list = []
                        comp_render = []
                        spec_render = []
                        rxn_render = []
                        #text_render = []
                        for  j in range ( 0, info.getNumColorDefinitions()):
                            color = info.getColorDefinition(j)
                            color_list.append([color.getId(),color.createValueString()])

                        for j in range (0, info.getNumStyles()):
                            style = info.getStyle(j)
                            group = style.getGroup()
                            typeList = style.createTypeString()
                            idList = style.createIdString()
                            if 'COMPARTMENTGLYPH' in typeList:
                                for k in range(len(color_list)):
                                    if color_list[k][0] == group.getFill():
                                        comp_fill_color = hex_to_rgb(color_list[k][1])
                                    if color_list[k][0] == group.getStroke():
                                        comp_border_color = hex_to_rgb(color_list[k][1])
                                comp_border_width = group.getStrokeWidth()
                                comp_render.append([idList,comp_fill_color,comp_border_color,comp_border_width])
                            elif 'SPECIESGLYPH' in typeList:
                                for k in range(len(color_list)):
                                    if color_list[k][0] == group.getFill():
                                        spec_fill_color = hex_to_rgb(color_list[k][1])
                                    if color_list[k][0] == group.getStroke():
                                        spec_border_color = hex_to_rgb(color_list[k][1])
                                spec_border_width = group.getStrokeWidth()
                                name_list = []
                                for element in group.getListOfElements():
                                    name = element.getElementName()
                                    name_list.append(name)
                                    try:
                                        NumRenderpoints = element.getListOfElements().getNumRenderPoints()
                                    except:
                                        NumRenderpoints = 0
                                if name == "ellipse": #circel and text-outside
                                    shapeIdx = 1
                                elif name == "polygon" and NumRenderpoints == 6:
                                    shapeIdx = 2
                                elif name == "polygon" and NumRenderpoints == 2:
                                    shapeIdx = 3
                                elif name == "polygon" and NumRenderpoints == 3:
                                    shapeIdx = 4
                                elif name == "rectangle" and spec_fill_color == '#ffffff' and spec_border_color == '#ffffff':
                                    shapeIdx = 5
                                #elif name == "ellipse" and flag_text_out == 1:
                                #    shapeIdx = 6
                                else: # name == "rectangle"/demo combo/others as default (rectangle)
                                    shapeIdx = 0
                                spec_render.append([idList,spec_fill_color,spec_border_color,spec_border_width,shapeIdx])

                            elif 'REACTIONGLYPH' in typeList:
                                for k in range(len(color_list)):
                                    if color_list[k][0] == group.getStroke():
                                        reaction_line_color = hex_to_rgb(color_list[k][1])
                                reaction_line_width = group.getStrokeWidth()
                                rxn_render.append([idList, reaction_line_color,reaction_line_width])
                        

            model = simplesbml.loadSBMLStr(sbmlStr)

            numFloatingNodes  = model.getNumFloatingSpecies()
            FloatingNodes_ids = model.getListOfFloatingSpecies()
            numBoundaryNodes  = model.getNumBoundarySpecies()
            BoundaryNodes_ids = model.getListOfBoundarySpecies()
            numRxns   = model.getNumReactions()
            Rxns_ids  = model.getListOfReactionIds()
            numComps  = model.getNumCompartments()
            Comps_ids = model.getListOfCompartmentIds()
            numNodes = numFloatingNodes + numBoundaryNodes


            comp_node_list = [0]*numComps #Note: numComps is different from numCompGlyphs
            for i in range(numComps):
                comp_node_list[i] = []


            #if there is layout info:
            if len(spec_id_list) != 0:
                for i in range(numComps):
                    temp_id = Comps_ids[i]
                    vol= model.getCompartmentVolume(i)
                    if temp_id == "_compartment_default_":
                        api.add_compartment(net_index, id=temp_id, volume = vol,
                        size=Vec2(3900,2400), position=Vec2(10,10),
                        fill_color = api.Color(255,255,255, 0), #the last digit for transparent
                        border_color = api.Color(255,255,255, 0),
                        border_width = comp_border_width)
                    else:
                        if len(comp_id_list) != 0:
                        #if mplugin is not None:                    
                            for j in range(numCompGlyphs):
                                if comp_id_list[j] == temp_id:
                                    dimension = comp_dimension_list[j]
                                    position = comp_position_list[j]
                            for j in range(len(comp_render)):
                                if temp_id == comp_render[j][0]:
                                    comp_fill_color = comp_render[j][1]
                                    comp_border_color = comp_render[j][2]
                                    comp_border_width = comp_render[j][3]

                        else:# no layout info about compartment,
                            # then the whole size of the canvas is the compartment size
                            # modify the compartment size using the max_rec function above
                            # random assigned network:
                            # dimension = [800,800]
                            # position = [40,40]
                            # the whole size of the compartment: 4000*2500
                            dimension = [3900,2400]
                            position = [10,10]
                            comp_fill_color = (255, 255, 255, 0)
                            comp_border_color = (255, 255, 255, 0)

                        api.add_compartment(net_index, id=temp_id, volume = vol,
                        size=Vec2(dimension[0],dimension[1]),position=Vec2(position[0],position[1]),
                        fill_color = api.Color(comp_fill_color[0],comp_fill_color[1],comp_fill_color[2]),
                        border_color = api.Color(comp_border_color[0],comp_border_color[1],comp_border_color[2]),
                        border_width = comp_border_width)

                id_list = []
                nodeIdx_list = [] #get_nodes idx do not follow the same order of add_node
                nodeIdx_specGlyph_list = []
                nodeIdx_specGlyph_alias_list = []
                numSpec_in_reaction = len(spec_specGlyph_id_list)
                #numSpecGlyphs is larger than numSpec_in_reaction if there orphan nodes
                # if numSpecGlyphs > numSpec_in_reaction:
                #   if showDialogues:
                #     wx.MessageBox("Orphan nodes are removed.", "Message", wx.OK | wx.ICON_INFORMATION)
                for i in range (numSpec_in_reaction):
                    temp_id = spec_specGlyph_id_list[i][0]
                    temp_concentration = spec_concentration_list[i]
                    tempGlyph_id = spec_specGlyph_id_list[i][1]
                    dimension = spec_dimension_list[i]
                    position = spec_position_list[i]
                    text_alignment = spec_text_alignment_list[i]
                    text_position = spec_text_position_list[i]
                    comp_id = model.getCompartmentIdSpeciesIsIn(temp_id)
                    for j in range(numFloatingNodes):
                        if temp_id == FloatingNodes_ids[j]:
                            if temp_id not in id_list:
                                for k in range(len(spec_render)):
                                    if temp_id == spec_render[k][0]:
                                        spec_fill_color = spec_render[k][1]
                                        spec_border_color = spec_render[k][2]
                                        spec_border_width = spec_render[k][3]
                                        shapeIdx = spec_render[k][4]
                                nodeIdx_temp = api.add_node(net_index, id=temp_id, floating_node = True,
                                size=Vec2(dimension[0],dimension[1]), position=Vec2(position[0],position[1]),
                                fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2]),
                                border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2]),
                                border_width=spec_border_width, shape_index=shapeIdx, concentration = temp_concentration)
                                api.set_node_shape_property(net_index, nodeIdx_temp, -1, "alignment", text_alignment)
                                api.set_node_shape_property(net_index, nodeIdx_temp, -1, "position", text_position)
                                id_list.append(temp_id)
                                nodeIdx_list.append(nodeIdx_temp)
                                nodeIdx_specGlyph_list.append([nodeIdx_temp,tempGlyph_id])
                            else:
                                index = id_list.index(temp_id)
                                nodeIdx_temp = api.add_alias(net_index, original_index=index,
                                size=Vec2(dimension[0],dimension[1]), position=Vec2(position[0],position[1]) )
                                api.set_node_shape_property(net_index, nodeIdx_temp, -1, "alignment", text_alignment)
                                api.set_node_shape_property(net_index, nodeIdx_temp, -1, "position", text_position)
                                id_list.append(temp_id)
                                nodeIdx_list.append(nodeIdx_temp)
                                nodeIdx_specGlyph_alias_list.append([nodeIdx_temp,tempGlyph_id])
                            for k in range(numCompGlyphs):
                                if len(comp_id_list) !=0 and comp_id == comp_id_list[k]:
                                    comp_node_list[k].append(nodeIdx_temp)
                    for j in range(numBoundaryNodes):
                        if temp_id == BoundaryNodes_ids[j]:
                            if temp_id not in id_list:
                                for k in range(len(spec_render)):
                                    if temp_id == spec_render[k][0]:
                                        spec_fill_color = spec_render[k][1]
                                        spec_border_color = spec_render[k][2]
                                        spec_border_width = spec_render[k][3]
                                        shapeIdx = spec_render[k][4]
                                nodeIdx_temp = api.add_node(net_index, id=temp_id, floating_node = False,
                                size=Vec2(dimension[0],dimension[1]), position=Vec2(position[0],position[1]),
                                fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2]),
                                border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2]),
                                border_width=spec_border_width, shape_index=shapeIdx, concentration = temp_concentration)
                                api.set_node_shape_property(net_index, nodeIdx_temp, -1, "alignment", text_alignment)
                                api.set_node_shape_property(net_index, nodeIdx_temp, -1, "position", text_position)
                                id_list.append(temp_id)
                                nodeIdx_list.append(nodeIdx_temp)
                                nodeIdx_specGlyph_list.append([nodeIdx_temp,tempGlyph_id])
                            else:
                                index = id_list.index(temp_id)
                                nodeIdx_temp = api.add_alias(net_index, original_index=index,
                                size=Vec2(dimension[0],dimension[1]), position=Vec2(position[0],position[1]))
                                api.set_node_shape_property(net_index, nodeIdx_temp, -1, "alignment", text_alignment)
                                api.set_node_shape_property(net_index, nodeIdx_temp, -1, "position", text_position)
                                id_list.append(temp_id)
                                nodeIdx_list.append(nodeIdx_temp)
                                nodeIdx_specGlyph_alias_list.append([nodeIdx_temp,tempGlyph_id])
                            for k in range(numCompGlyphs):
                                if len(comp_id) != 0 and comp_id == comp_id_list[k]:
                                    comp_node_list[k].append(nodeIdx_temp)

                if len(comp_id_list) != 0:
                    for i in range(numComps):
                        temp_id = Comps_ids[i]
                        if temp_id == '_compartment_default_': 
                            #numNodes is different from len(nodeIdx_list) because of alias node
                            node_list_default = [item for item in range(len(nodeIdx_list))]
                            for j in range(len(node_list_default)):
                                try:
                                    api.set_compartment_of_node(net_index=net_index, node_index=node_list_default[j], comp_index=i) 
                                except:
                                    pass # Orphan nodes are removed
                        for j in range(numCompGlyphs):
                            if comp_id_list[j] == temp_id:
                                node_list_temp = comp_node_list[j]
                            else:
                                node_list_temp = []
                            for k in range(len(node_list_temp)):
                                api.set_compartment_of_node(net_index=net_index, node_index=node_list_temp[k], comp_index=i)
                else:
                    for i in range(len(nodeIdx_list)):
                        api.set_compartment_of_node(net_index=net_index, node_index=nodeIdx_list[i], comp_index=0)


                nodeIdx_specGlyph_whole_list = nodeIdx_specGlyph_list + nodeIdx_specGlyph_alias_list

                for i in range (numReactionGlyphs):
                    src = []
                    dst = []
                    temp_id = reaction_id_list[i]
                    kinetics = kinetics_list[i]
                    rct_num = len(rct_specGlyph_list[i])
                    prd_num = len(prd_specGlyph_list[i])

                    for j in range(rct_num):
                        temp_specGlyph_id = rct_specGlyph_list[i][j]
                        for k in range(numSpec_in_reaction):
                            if temp_specGlyph_id == nodeIdx_specGlyph_whole_list[k][1]:
                                rct_idx = nodeIdx_specGlyph_whole_list[k][0]
                        src.append(rct_idx)

                    for j in range(prd_num):
                        temp_specGlyph_id = prd_specGlyph_list[i][j]
                        for k in range(numSpec_in_reaction):
                            if temp_specGlyph_id == nodeIdx_specGlyph_whole_list[k][1]:
                                prd_idx = nodeIdx_specGlyph_whole_list[k][0]
                        dst.append(prd_idx)

                    for j in range(len(rxn_render)):
                        if temp_id == rxn_render[j][0]:
                            reaction_line_color = rxn_render[j][1]
                            reaction_line_width = rxn_render[j][2]

                    try:
                        center_position = reaction_center_list[i]
                        idx = api.add_reaction(net_index, id=temp_id, reactants=src, products=dst,
                        fill_color=api.Color(reaction_line_color[0],reaction_line_color[1],reaction_line_color[2]),
                        line_thickness=reaction_line_width)
                        api.update_reaction(net_index, idx, ratelaw = kinetics)
                        #control of center_pos and handles(handles do not work so far)
                        handles = api.default_handle_positions(net_index, idx)
                        handles[0]= Vec2(center_position[0],center_position[1])
                        api.update_reaction(net_index, idx, center_pos = Vec2(center_position[0],center_position[1]), handle_positions=handles)

                    except: #There is no info about the center_pos, so set as default
                        idx = api.add_reaction(net_index, id=temp_id, reactants=src, products=dst,
                        fill_color=api.Color(reaction_line_color[0],reaction_line_color[1],reaction_line_color[2]),
                        line_thickness=reaction_line_width)
                        api.update_reaction(net_index, idx, ratelaw = kinetics)
            
            else: # there is no layout information, assign position randomly and size as default
                comp_id_list = Comps_ids

                for i in range(numComps):
                    temp_id = Comps_ids[i]
                    vol= model.getCompartmentVolume(i)
                    dimension = [3900,2400]
                    position = [10,10]

                    api.add_compartment(net_index, id=temp_id, volume = vol,
                    size=Vec2(dimension[0],dimension[1]),position=Vec2(position[0],position[1]),
                    fill_color = api.Color(comp_fill_color[0],comp_fill_color[1],comp_fill_color[2]),
                    border_color = api.Color(comp_border_color[0],comp_border_color[1],comp_border_color[2]),
                    border_width = comp_border_width)

                for i in range (numFloatingNodes):
                    temp_id = FloatingNodes_ids[i]
                    comp_id = model.getCompartmentIdSpeciesIsIn(temp_id)
                    try:
                        temp_concentration = model.getSpeciesInitialConcentration(temp_id)
                    except:
                        temp_concentration = 1.0
                    nodeIdx_temp = api.add_node(net_index, id=temp_id, size=Vec2(60,40), floating_node = True,
                    position=Vec2(40 + math.trunc (_random.random()*800), 40 + math.trunc (_random.random()*800)),
                    fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2]),
                    border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2]),
                    border_width=spec_border_width, shape_index=shapeIdx, concentration=temp_concentration)
                    for j in range(numComps):
                        if comp_id == comp_id_list[j]:
                            comp_node_list[j].append(nodeIdx_temp)

                for i in range (numBoundaryNodes):
                    temp_id = BoundaryNodes_ids[i]
                    comp_id = model.getCompartmentIdSpeciesIsIn(temp_id)
                    try:
                        temp_concentration = model.getSpeciesInitialConcentration(temp_id)
                    except:
                        temp_concentration = 1.0
                    nodeIdx_temp = api.add_node(net_index, id=temp_id, size=Vec2(60,40), floating_node = False,
                    position=Vec2(40 + math.trunc (_random.random()*800), 40 + math.trunc (_random.random()*800)),
                    fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2]),
                    border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2]),
                    border_width=spec_border_width, shape_index=shapeIdx, concentration=temp_concentration)
                    for j in range(numComps):
                        if comp_id == comp_id_list[j]:
                            comp_node_list[j].append(nodeIdx_temp)


                for i in range(numComps):
                    temp_id = Comps_ids[i]
                    for j in range(numComps):
                        if comp_id_list[j] == temp_id:
                            node_list_temp = comp_node_list[j]
                        for k in range(len(node_list_temp)):
                            api.set_compartment_of_node(net_index=net_index, node_index=node_list_temp[k], comp_index=i)

                numNodes = api.node_count(net_index)
                allNodes = api.get_nodes(net_index)


                flag_add_rxn_err = 0
                dummy_node_id_index = 0
                for i in range (numRxns):
                    src = []
                    dst = []
                    temp_id = Rxns_ids[i]
                    kinetics = model.getRateLaw(i)
                    rct_num = model.getNumReactants(i)
                    prd_num = model.getNumProducts(i)


                    for j in range(rct_num):
                        rct_id = model.getReactant(temp_id,j)
                        for k in range(numNodes):
                            if allNodes[k].id == rct_id:
                                src.append(allNodes[k].index)


                    for j in range(prd_num):
                        prd_id = model.getProduct(temp_id,j)
                        for k in range(numNodes):
                            if allNodes[k].id == prd_id:
                                dst.append(allNodes[k].index)                   

                    try: 
                        src_corr = []
                        [src_corr.append(x) for x in src if x not in src_corr]

                        dst_corr = []
                        [dst_corr.append(x) for x in dst if x not in dst_corr]

                        if len(src_corr) == 0:
                            temp_node_id = "dummy" + str(dummy_node_id_index)                   
                            comp_node_id = allNodes[dst_corr[0]].id 
                            # assume the dummy node is in the same compartment as the first src/dst node
                            comp_id = model.getCompartmentIdSpeciesIsIn(comp_node_id)
                            nodeIdx_temp = api.add_node(net_index, id=temp_node_id, size=Vec2(60,40), floating_node = True,
                            position=Vec2(40 + math.trunc (_random.random()*800), 40 + math.trunc (_random.random()*800)),
                            fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2]),
                            border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2]),
                            border_width=spec_border_width, shape_index=shapeIdx)
                            
                            src_corr.append(nodeIdx_temp)
                            dummy_node_id_index += 1

                            for i in range(numComps):
                                if comp_id == Comps_ids[i]:
                                    api.set_compartment_of_node(net_index=net_index, node_index=nodeIdx_temp, comp_index=i)
                        
                        if len(dst_corr) == 0:
                            temp_node_id = "dummy" + str(dummy_node_id_index)                   
                            comp_node_id = allNodes[src_corr[0]].id
                            comp_id = model.getCompartmentIdSpeciesIsIn(comp_node_id)
                            nodeIdx_temp = api.add_node(net_index, id=temp_node_id, size=Vec2(60,40), floating_node = True,
                            position=Vec2(40 + math.trunc (_random.random()*800), 40 + math.trunc (_random.random()*800)),
                            fill_color=api.Color(spec_fill_color[0],spec_fill_color[1],spec_fill_color[2]),
                            border_color=api.Color(spec_border_color[0],spec_border_color[1],spec_border_color[2]),
                            border_width=spec_border_width, shape_index=shapeIdx)
                            
                            dst_corr.append(nodeIdx_temp)
                            dummy_node_id_index += 1

                            for i in range(numComps):
                                if comp_id == Comps_ids[i]:
                                    api.set_compartment_of_node(net_index=net_index, node_index=nodeIdx_temp, comp_index=i)
    
                        idx = api.add_reaction(net_index, id=temp_id, reactants=src_corr, products=dst_corr,
                        fill_color=api.Color(reaction_line_color[0],reaction_line_color[1],reaction_line_color[2]),
                        line_thickness=reaction_line_width)
                        api.update_reaction(net_index, idx, ratelaw = kinetics)


                        #set the information for handle positions, center positions and use bezier as default
                    
                    except:
                        flag_add_rxn_err = 1


                # if flag_add_rxn_err == 1:
                #     wx.MessageBox("There are errors while loading this SBML file!", "Message", wx.OK | wx.ICON_INFORMATION)
                


          


