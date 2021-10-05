"""
Export the network on canvas to an SBML string as save it as a file.
Version 0.02: Author: Jin Xu (2021)
"""


# pylint: disable=maybe-no-member

from inspect import Parameter
import wx
from wx.core import Width
from rkviewer.plugin.classes import PluginMetadata, WindowedPlugin, PluginCategory
from rkviewer.plugin import api
from rkviewer.plugin.api import Node, Vec2, Reaction, Color, get_node_by_index
import os
from libsbml import * # does not have to import in the main.py too
import re # to process kinetic_law string

class ExportSBML(WindowedPlugin):
    metadata = PluginMetadata(
        name='ExportSBML',
        author='Jin Xu',
        version='0.5.1',
        short_desc='Export SBML.',
        long_desc='Export the SBML String from the network on canvas and save it to a file.',
        category=PluginCategory.ANALYSIS
    )


    def create_window(self, dialog):
        """
        Create a window to export the SBML.
        Args:
            self
            dialog
        """
        self.window = wx.Panel(dialog, pos=(5,100), size=(300, 320))

        show_btn = wx.Button(self.window, -1, 'Export', (5, 5))
        show_btn.Bind(wx.EVT_BUTTON, self.Show)

        copy_btn = wx.Button(self.window, -1, 'Copy To Clipboard', (83, 5))
        copy_btn.Bind(wx.EVT_BUTTON, self.Copy)

        save_btn = wx.Button(self.window, -1, 'Save', (205, 5))
        save_btn.Bind(wx.EVT_BUTTON, self.Save)

        wx.StaticText(self.window, -1, 'SBML string:', (5,30))
        self.SBMLText = wx.TextCtrl(self.window, -1, "", (10, 50), size=(260, 220), style=wx.TE_MULTILINE|wx.HSCROLL)
        self.SBMLText.SetInsertionPoint(0)

        return self.window

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


    def Show(self, evt):
        """
        Handler for the "Export" button.
        """
        sbmlStr_layout_render = self.NetworkToSBML()
        self.SBMLText.SetValue(sbmlStr_layout_render)

    def NetworkToSBML(self):
        """
        Get the network on canvas and change it to an SBML string
        """

        def getSymbols(kinetic_law):
            str = kinetic_law
            str = str.replace(' ', '')  
            list = re.split('[+|\-|*|/|(|)]', str)
            list = [i for i in list if i != '']
            res = []
            [res.append(x) for x in list if x not in res and not x.isdigit()]
            return res


        isReversible = True
        netIn = 0
        numNodes = api.node_count(netIn)
        numReactions = api.reaction_count(netIn)
        
        if numNodes == 0 or numReactions == 0 :
            wx.MessageBox("Please import a network with at least one reaction on canvas", "Message", wx.OK | wx.ICON_INFORMATION)
        else:
            allNodes = api.get_nodes(netIn)
            allReactions = api.get_reactions(netIn)
            allcompartments = api.get_compartments(netIn)
            numCompartments = len(allcompartments)      
#######################################

            # Creates an SBMLNamespaces object with the given SBML level, version
            # package name, package version.
            # 
            # (NOTE) By default, the name of package (i.e. "layout") will be used
            # if the argument for the prefix is missing or empty. Thus the argument
            # for the prefix can be added as follows:
            # 
            #    SBMLNamespaces sbmlns(3,1,"layout",1,"LAYOUT")
            # 
            sbmlns = SBMLNamespaces(3, 1, "layout", 1)
            # create the document
            document = SBMLDocument(sbmlns)
            # set the "required" attribute of layout package  to "true"
            document.setPkgRequired("layout", False)  

            # create the Model
            model = document.createModel()
            model.setId("Model_layout")
            document.setModel(model)

            # create the Compartment and species

            comp_id_list = []
            for i in range(numCompartments):
                comp_id_list.append(allcompartments[i].id) 


            if numCompartments != 0:
                if "_compartment_default_" not in comp_id_list:
                    compartment = model.createCompartment()
                    comp_id="_compartment_default_"
                    compartment.setId(comp_id)
                    compartment.setConstant(True)
                
                for i in range(numCompartments):   
                    compartment = model.createCompartment()
                    comp_id=allcompartments[i].id
                    compartment.setId(comp_id)
                    compartment.setConstant(True)
                spec_id_list = []
                for i in range(numNodes):
                    original_index = allNodes[i].original_index
                    if original_index == -1:
                        spec_id = allNodes[i].id
                        if spec_id not in spec_id_list:
                            spec_id_list.append(spec_id)
                        species = model.createSpecies()
                        species.setId(spec_id)
                        comp_idx = allNodes[i].comp_idx
                        if comp_idx != -1:
                            comp_id = allcompartments[comp_idx].id 
                            species.setCompartment(comp_id)  
                        else:
                            species.setCompartment("_compartment_default_") 
                        species.setInitialConcentration(allNodes[i].concentration)	
                        species.setHasOnlySubstanceUnits(False)
                        species.setBoundaryCondition(False)
                        species.setConstant(False)             
                        if allNodes[i].floating_node == False:
                            species.setBoundaryCondition(True)
                            species.setConstant(True)   
            else: #set default compartment
                compartment = model.createCompartment()
                comp_id="_compartment_default_"
                compartment.setId(comp_id)
                compartment.setConstant(True)
                spec_id_list = []
                for i in range(numNodes):
                    original_index = allNodes[i].original_index
                    if original_index == -1:
                        spec_id = allNodes[i].id
                        if spec_id not in spec_id_list:
                            spec_id_list.append(spec_id)
                        species = model.createSpecies()
                        species.setId(spec_id)
                        species.setCompartment(comp_id)
                        species.setInitialConcentration(allNodes[i].concentration)	
                        species.setHasOnlySubstanceUnits(False)
                        species.setBoundaryCondition(False)
                        species.setConstant(False)             
                        if allNodes[i].floating_node == False:
                            species.setBoundaryCondition(True)
                            species.setConstant(True)
            # create reactions:
            for i in range(numReactions):
                reaction_id = allReactions[i].id
                rct = [] # id list of the rcts
                prd = []
                rct_num = len(allReactions[i].sources)
                prd_num = len(allReactions[i].targets)
                for j in range(rct_num):
                    rct.append(get_node_by_index(netIn, allReactions[i].sources[j]).id)
                for j in range(prd_num):
                    prd.append(get_node_by_index(netIn, allReactions[i].targets[j]).id)

                kinetic_law_from_user = allReactions[i].rate_law
                
                if kinetic_law_from_user == '':
                    kinetic_law = ''
                    parameter_list = []
                    kinetic_law = kinetic_law + 'E' + str (i) + '*(k' + str (i) 
                    parameter_list.append('E' + str (i))
                    parameter_list.append('k' + str (i))
                    for j in range(rct_num):
                        kinetic_law = kinetic_law + '*' + rct[j]
                        
                    if isReversible:
                        kinetic_law = kinetic_law + ' - k' + str (i) + 'r'
                        parameter_list.append('k' + str (i) + 'r')
                        for j in range(prd_num):
                            kinetic_law = kinetic_law + '*' + prd[j]
                    kinetic_law = kinetic_law + ')'
                else:
                    kinetic_law = kinetic_law_from_user
                    parameter_spec_list = getSymbols(kinetic_law_from_user) 
                    parameter_list = []
                    for j in range(len(parameter_spec_list)):
                        if parameter_spec_list[j] not in spec_id_list:
                            parameter_list.append(parameter_spec_list[j])
                    if len(parameter_list) == 0: #If the input kinetic law is invalid
                        kinetic_law = ''
                        parameter_list = []
                        kinetic_law = kinetic_law + 'E' + str (i) + '*(k' + str (i) 
                        parameter_list.append('E' + str (i))
                        parameter_list.append('k' + str (i))
                        for j in range(rct_num):
                            kinetic_law = kinetic_law + '*' + rct[j]
                            
                        if isReversible:
                            kinetic_law = kinetic_law + ' - k' + str (i) + 'r'
                            parameter_list.append('k' + str (i) + 'r')
                            for j in range(prd_num):
                                kinetic_law = kinetic_law + '*' + prd[j]
                        kinetic_law = kinetic_law + ')'

                    
                reaction = model.createReaction()
                reaction.setId(allReactions[i].id)
                reaction.setReversible(False)
                reaction.setFast(False)
                if isReversible:
                    reaction.setReversible(True)
                for j in range(len(parameter_list)):
                    parameters = model.createParameter()
                    parameters.setId(parameter_list[j])
                    parameters.setValue(0.1)
                    parameters.setConstant(True)
                kinetics = reaction.createKineticLaw()
                kinetics.setFormula(kinetic_law)
                

                for j in range(rct_num):
                    reference = reaction.createReactant()
                    reference.setSpecies(rct[j])
                    ref_id = "SpecRef_" + reaction_id + "_rct" + str(j)
                    reference.setId(ref_id)
                    reference.setStoichiometry(1.)
                    reference.setConstant(False)

                for j in range(prd_num):
                    reference = reaction.createProduct()
                    reference.setSpecies(prd[j])
                    ref_id = "SpecRef_" + reaction_id + "_prd" + str(j)
                    reference.setId(ref_id)
                    reference.setStoichiometry(1.)
                    reference.setConstant(False)

            # create the Layout

            #
            # set the LayoutPkgNamespaces for Level 3 Version1 Layout Version 1
            #
            layoutns = LayoutPkgNamespaces(3, 1, 1)

            renderns = RenderPkgNamespaces(3, 1, 1)

            #
            # Get a LayoutModelPlugin object plugged in the model object.
            #
            # The type of the returned value of SBase::getPlugin() function is SBasePlugin, and
            # thus the value needs to be casted for the corresponding derived class.
            #

            mplugin = model.getPlugin("layout")

            # rPlugin = model.getPlugin("render")
            # if rPlugin is None:
            #   print("there is no render outside layout.")
                 
            # lolPlugin = mplugin.getListOfLayouts().getPlugin("render")
            # if lolPlugin is None:
            #   print("there is no render info inside layout.")
            
            if mplugin is None:
                # print(
                #     "[Fatal Error] Layout Extension Level " + layoutns.getLevel() + " Version " + layoutns.getVersion() + " package version " + layoutns.getPackageVersion() + " is not registered.")
                # sys.exit(1)
                wx.MessageBox("There is no layout information.", "Message", wx.OK | wx.ICON_INFORMATION)


            #
            # Creates a Layout object via LayoutModelPlugin object.
            #
            layout = mplugin.createLayout()
            layout.setId("Layout_1")
            layout.setDimensions(Dimensions(layoutns, 800.0, 800.0))
            # random network (40+800x, 40+800y)

            #create the CompartmentGlyph and SpeciesGlyphs
            if numCompartments != 0:
                for i in range(numCompartments):   
                    comp_id=allcompartments[i].id
                    if comp_id != "_compartment_default_":
                        compartmentGlyph = layout.createCompartmentGlyph()
                        compG_id = "CompG_" + comp_id
                        compartmentGlyph.setId(compG_id)
                        compartmentGlyph.setCompartmentId(comp_id)
                        bb_id  = "bb_" + comp_id
                        pos_x  = allcompartments[i].position.x
                        pos_y  = allcompartments[i].position.y
                        width  = allcompartments[i].size.x
                        height = allcompartments[i].size.y
                        compartmentGlyph.setBoundingBox(BoundingBox(layoutns, bb_id, pos_x, pos_y, width, height))
                for i in range(numNodes):   
                    spec_id = allNodes[i].id
                    spec_index = allNodes[i].index
                    # spec_shapeIdx = allNodes[i].shape_index
                    primitive, _ = allNodes[i].shape.text_item
                    alignment_value = primitive.alignment.value
                    position_value = primitive.position.value
                    speciesGlyph = layout.createSpeciesGlyph()
                    specG_id = "SpecG_"  + spec_id + '_idx_' + str(spec_index)
                    speciesGlyph.setId(specG_id)
                    speciesGlyph.setSpeciesId(spec_id)
                    bb_id  = "bb_" + spec_id + '_idx_' + str(spec_index)
                    pos_x  = allNodes[i].position.x
                    pos_y  = allNodes[i].position.y
                    width  = allNodes[i].size.x
                    height = allNodes[i].size.y
                    speciesGlyph.setBoundingBox(BoundingBox(layoutns, bb_id, pos_x, pos_y, width, height))

                    textGlyph = layout.createTextGlyph()
                    textG_id = "TextG_" + spec_id + '_idx_' + str(spec_index)
                    textGlyph.setId(textG_id)
                    bb_id  = "bb_spec_text_" + spec_id + '_idx_' + str(spec_index)
                    # if spec_shapeIdx == 6: #rough by eyes
                    #     pos_x_text = pos_x + 50
                    #     pos_y_text = pos_y + 30
                    # else:
                    pos_x_text = pos_x
                    pos_y_text = pos_y
                    #rough position, if text is outside the node
                    if position_value != 1: #not inside the node
                        if alignment_value == 1: #LEFT
                            pos_x_text = pos_x - width 
                        if alignment_value == 3: #RIGHT
                            pos_x_text = pos_x + width                           
                    if position_value == 2: #ABOVE
                        pos_y_text = pos_y - height
                    if position_value == 3: #BELOW
                        pos_y_text = pos_y + height 
                    textGlyph.setBoundingBox(BoundingBox(layoutns, bb_id, pos_x_text, pos_y_text, width, height))
                    textGlyph.setOriginOfTextId(specG_id)
                    textGlyph.setGraphicalObjectId(specG_id)
            else:#there is no compartment  
                comp_id= "_compartment_default_"
                compartmentGlyph = layout.createCompartmentGlyph()
                compG_id = "CompG_" + comp_id
                compartmentGlyph.setId(compG_id)
                compartmentGlyph.setCompartmentId(comp_id)
                bb_id  = "bb_" + comp_id
                pos_x  = 10
                pos_y  = 10
                width  = 3900
                height = 2400
                compartmentGlyph.setBoundingBox(BoundingBox(layoutns, bb_id, pos_x, pos_y, width, height))
            
                for i in range(numNodes):
                    spec_id = allNodes[i].id
                    spec_index = allNodes[i].index
                    #spec_shapeIdx = allNodes[i].shape_index
                    primitive, _ = allNodes[i].shape.text_item
                    alignment_value = primitive.alignment.value
                    position_value = primitive.position.value
                    speciesGlyph = layout.createSpeciesGlyph()
                    specG_id = "SpecG_"  + spec_id + '_idx_' + str(spec_index)
                    speciesGlyph.setId(specG_id)
                    speciesGlyph.setSpeciesId(spec_id)
                    bb_id  = "bb_" + spec_id + '_idx_' + str(spec_index)
                    pos_x  = allNodes[i].position.x
                    pos_y  = allNodes[i].position.y
                    width  = allNodes[i].size.x
                    height = allNodes[i].size.y
                    speciesGlyph.setBoundingBox(BoundingBox(layoutns, bb_id, pos_x, pos_y, width, height))

                    textGlyph = layout.createTextGlyph()
                    textG_id = "TextG_" + spec_id + '_idx_' + str(spec_index)
                    textGlyph.setId(textG_id)
                    # if spec_shapeIdx == 6: #rough by eyes
                    #     pos_x_text = pos_x + 50
                    #     pos_y_text = pos_y + 30
                    # else:
                    pos_x_text = pos_x
                    pos_y_text = pos_y
                    #rough position, if text is outside the node
                    if position_value != 1: #not inside the node
                        if alignment_value == 1: #LEFT
                            pos_x_text = pos_x - width 
                        if alignment_value == 3: #RIGHT
                            pos_x_text = pos_x + width                           
                    if position_value == 2: #ABOVE
                        pos_y_text = pos_y - height
                    if position_value == 3: #BELOW
                        pos_y_text = pos_y + height
                    bb_id  = "bb_spec_text_" + spec_id + '_idx_' + str(spec_index)
                    textGlyph.setBoundingBox(BoundingBox(layoutns, bb_id, pos_x_text, pos_y_text, width, height))
                    textGlyph.setOriginOfTextId(specG_id)
                    textGlyph.setGraphicalObjectId(specG_id)

            # create the ReactionGlyphs and SpeciesReferenceGlyphs
            for i in range(numReactions):
                reaction_id = allReactions[i].id
                center_pos = allReactions[i].center_pos
                centroid = api.compute_centroid(netIn, allReactions[i].sources, allReactions[i].targets)
                try:
                    center_value = [center_pos.x,center_pos.y]
                except:
                    center_value = [centroid.x,centroid.y]
                
                reactionGlyph = layout.createReactionGlyph()
                reactionG_id = "RectionG_" + reaction_id
                reactionGlyph.setId(reactionG_id)
                reactionGlyph.setReactionId(reaction_id)
                
                reactionCurve = reactionGlyph.getCurve()
                ls = reactionCurve.createLineSegment()
                ls.setStart(Point(layoutns, center_value[0], center_value[1]))
                ls.setEnd(Point(layoutns, center_value[0], center_value[1]))

                rct = [] # id list of the rcts
                prd = []
                rct_index = []
                prd_index = []
                rct_num = len(allReactions[i].sources)
                prd_num = len(allReactions[i].targets)


                for j in range(rct_num):
                    rct.append(get_node_by_index(netIn, allReactions[i].sources[j]).id)
                    rct_index.append(get_node_by_index(netIn, allReactions[i].sources[j]).index)
                for j in range(prd_num):
                    prd.append(get_node_by_index(netIn, allReactions[i].targets[j]).id)
                    prd_index.append(get_node_by_index(netIn, allReactions[i].targets[j]).index)
                for j in range(rct_num):
                    ref_id = "SpecRef_" + reaction_id + "_rct" + str(j)

                    speciesReferenceGlyph = reactionGlyph.createSpeciesReferenceGlyph()
                    specsRefG_id = "SpecRefG_" + reaction_id + "_rct" + str(j)
                    specG_id = "SpecG_" + rct[j] + '_idx_' + str(rct_index[j])
                    speciesReferenceGlyph.setId(specsRefG_id)
                    speciesReferenceGlyph.setSpeciesGlyphId(specG_id)
                    speciesReferenceGlyph.setSpeciesReferenceId(ref_id)
                    speciesReferenceGlyph.setRole(SPECIES_ROLE_SUBSTRATE)
                    speciesReferenceCurve = speciesReferenceGlyph.getCurve()
                    cb = speciesReferenceCurve.createCubicBezier()

                    cb.setStart(Point(layoutns, center_value[0], center_value[1]))

                    handle1 = api.get_reaction_center_handle(netIn, allReactions[i].index)
                    handle2 = api.get_reaction_node_handle(netIn, allReactions[i].index,
                     allReactions[i].sources[j],is_source=True)
                    cb.setBasePoint1(Point(layoutns, handle1.x, handle1.y))
                    cb.setBasePoint2(Point(layoutns, handle2.x, handle2.y))

                    pos_x = get_node_by_index(netIn,allReactions[i].sources[j]).position.x
                    pos_y = get_node_by_index(netIn,allReactions[i].sources[j]).position.y
                    width = get_node_by_index(netIn,allReactions[i].sources[j]).size.x
                    height = get_node_by_index(netIn,allReactions[i].sources[j]).size.y
                    cb.setEnd(Point(layoutns, pos_x + 0.5*width, pos_y - 0.5*height))

                for j in range(prd_num):
                    ref_id = "SpecRef_" + reaction_id + "_prd" + str(j)
                    speciesReferenceGlyph = reactionGlyph.createSpeciesReferenceGlyph()
                    specsRefG_id = "SpecRefG_" + reaction_id + "_prd" + str(j)
                    specG_id = "SpecG_" + prd[j]  + '_idx_' + str(prd_index[j])
                    speciesReferenceGlyph.setId(specsRefG_id)
                    speciesReferenceGlyph.setSpeciesGlyphId(specG_id)
                    speciesReferenceGlyph.setSpeciesReferenceId(ref_id)
                    speciesReferenceGlyph.setRole(SPECIES_ROLE_PRODUCT)

                    speciesReferenceCurve = speciesReferenceGlyph.getCurve()
                    cb = speciesReferenceCurve.createCubicBezier()
                    cb.setStart(Point(layoutns, center_value[0], center_value[1]))

                    handle1 = api.get_reaction_center_handle(netIn, allReactions[i].index)
                    handle2 = api.get_reaction_node_handle(netIn, allReactions[i].index,
                     allReactions[i].targets[j],is_source=False)
                    cb.setBasePoint1(Point(layoutns, handle1.x, handle1.y))
                    cb.setBasePoint2(Point(layoutns, handle2.x, handle2.y))

                    pos_x = get_node_by_index(netIn, allReactions[i].targets[j]).position.x
                    pos_y = get_node_by_index(netIn, allReactions[i].targets[j]).position.y
                    width = get_node_by_index(netIn, allReactions[i].targets[j]).size.x
                    height = get_node_by_index(netIn, allReactions[i].targets[j]).size.y
                    cb.setEnd(Point(layoutns, pos_x + 0.5*width, pos_y - 0.5*height))

            sbmlStr_layout = writeSBMLToString(document) #sbmlStr is w/o layout info 

            doc = readSBMLFromString(sbmlStr_layout)
            model_layout = doc.getModel()
            mplugin = model_layout.getPlugin("layout")

            # add render information to the first layout
            layout = mplugin.getLayout(0)

            rPlugin = layout.getPlugin("render")

            uri = RenderExtension.getXmlnsL2() if doc.getLevel() == 2 else RenderExtension.getXmlnsL3V1V1();

            # enable render package
            doc.enablePackage(uri, "render", True)
            doc.setPackageRequired("render", False)

            rPlugin = layout.getPlugin("render")

            rInfo = rPlugin.createLocalRenderInformation()
            rInfo.setId("info")
            rInfo.setName("Render Information")
            rInfo.setProgramName("RenderInformation")
            rInfo.setProgramVersion("1.0")

            # add some colors
            # color = rInfo.createColorDefinition()
            # color.setId("black")
            # color.setColorValue("#000000")
            
            if numCompartments != 0:  
                for i in range(len(allcompartments)):
                    comp_id = allcompartments[i].id
                    if comp_id != '_compartment_default':
                        fill_color        = allcompartments[i].fill_color
                        border_color      = allcompartments[i].border_color
                        comp_border_width = allcompartments[i].border_width
                        fill_color_str    = '#%02x%02x%02x' % (fill_color.r,fill_color.g,fill_color.b)
                        border_color_str  = '#%02x%02x%02x' % (border_color.r,border_color.g,border_color.b)
                    

                        color = rInfo.createColorDefinition()
                        color.setId("comp_fill_color" + "_" + comp_id)
                        color.setColorValue(fill_color_str)

                        color = rInfo.createColorDefinition()
                        color.setId("comp_border_color" + "_" + comp_id)
                        color.setColorValue(border_color_str)

                        # add a list of styles 
                        style = rInfo.createStyle("compStyle" + "_" + comp_id)
                        style.getGroup().setFillColor("comp_fill_color" + "_" + comp_id)
                        style.getGroup().setStroke("comp_border_color" + "_" + comp_id)
                        style.getGroup().setStrokeWidth(comp_border_width)
                        style.addType("COMPARTMENTGLYPH")
                        style.addId(comp_id)
                        rectangle = style.getGroup().createRectangle()
                        rectangle.setCoordinatesAndSize(RelAbsVector(0,0),RelAbsVector(0,0),RelAbsVector(0,0),RelAbsVector(0,100),RelAbsVector(0,100))

            else:
                comp_border_width = 2.
                #set default compartment with white color
                fill_color_str = '#00ffffff'
                border_color_str = '#00ffffff'

                color = rInfo.createColorDefinition()
                color.setId("comp_fill_color")
                color.setColorValue(fill_color_str)

                color = rInfo.createColorDefinition()
                color.setId("comp_border_color")
                color.setColorValue(border_color_str)

                # add a list of styles 
                style = rInfo.createStyle("compStyle")
                style.getGroup().setFillColor("comp_fill_color")
                style.getGroup().setStroke("comp_border_color")
                style.getGroup().setStrokeWidth(comp_border_width)
                style.addType("COMPARTMENTGLYPH")
                style.addId(comp_id)
                rectangle = style.getGroup().createRectangle()
                rectangle.setCoordinatesAndSize(RelAbsVector(0,0),RelAbsVector(0,0),RelAbsVector(0,0),RelAbsVector(0,100),RelAbsVector(0,100))
    
            for i in range(len(allNodes)):
                node =  allNodes[i]
                spec_id = node.id
                try: 
                    primitive, _ = node.shape.items[0]
                    spec_fill_color   = primitive.fill_color
                    spec_border_color = primitive.border_color
                    spec_fill_color_str   = '#%02x%02x%02x' % (spec_fill_color.r,spec_fill_color.g,spec_fill_color.b)
                    spec_border_color_str = '#%02x%02x%02x' % (spec_border_color.r,spec_border_color.g,spec_border_color.b)
                    spec_border_width = primitive.border_width
                    primitive, _ = node.shape.text_item
                    text_font_size = primitive.font_size
                    font_color = primitive.font_color
                    text_line_color_str =  '#%02x%02x%02x' % (font_color.r,font_color.g,font_color.b)
                except:#text-only
                    #set default species/node with white color
                    #spec_fill_color_str = '#ffffff'
                    #spec_border_color_str = '#ffffff'
                    spec_fill_color_str = '#00ffffff'
                    spec_border_color_str = '#00ffffff'
                    spec_border_width = 2.
                    text_font_size = 11
                    text_line_color_str = '#000000'


                color = rInfo.createColorDefinition()
                color.setId("spec_fill_color" + "_" + spec_id)
                color.setColorValue(spec_fill_color_str)

                color = rInfo.createColorDefinition()
                color.setId("spec_border_color" + "_" + spec_id)
                color.setColorValue(spec_border_color_str)

                color = rInfo.createColorDefinition()
                color.setId("text_line_color" + "_" + spec_id)
                color.setColorValue(text_line_color_str)

                style = rInfo.createStyle("specStyle" + "_" + spec_id)
                style.getGroup().setFillColor("spec_fill_color" + "_" + spec_id)
                style.getGroup().setStroke("spec_border_color" + "_" + spec_id)
                style.getGroup().setStrokeWidth(spec_border_width)
                style.addType("SPECIESGLYPH")
                style.addId(spec_id)
                if node.shape_index == 1 or node.shape_index == 6: #ellipse/text-outside
                    ellipse = style.getGroup().createEllipse()
                    ellipse.setCenter2D(RelAbsVector(0, 50), RelAbsVector(0, 50))
                    ellipse.setRadii(RelAbsVector(0, 100), RelAbsVector(0, 100))
                
                elif node.shape_index == 2: #hexagon(6)
                    polygon = style.getGroup().createPolygon()
                    renderPoint1 = polygon.createPoint()
                    renderPoint1.setCoordinates(RelAbsVector(0,100), RelAbsVector(0,50))
                    renderPoint2 = polygon.createPoint()
                    renderPoint2.setCoordinates(RelAbsVector(0,75), RelAbsVector(0,7))
                    renderPoint3 = polygon.createPoint()
                    renderPoint3.setCoordinates(RelAbsVector(0,25), RelAbsVector(0,7))
                    renderPoint4 = polygon.createPoint()
                    renderPoint4.setCoordinates(RelAbsVector(0,0), RelAbsVector(0,50))
                    renderPoint5 = polygon.createPoint()
                    renderPoint5.setCoordinates(RelAbsVector(0,25), RelAbsVector(0,86))
                    renderPoint6 = polygon.createPoint()
                    renderPoint6.setCoordinates(RelAbsVector(0,75), RelAbsVector(0,86))
                elif node.shape_index == 3: #line(2)
                    polygon = style.getGroup().createPolygon()
                    renderPoint1 = polygon.createPoint()
                    renderPoint1.setCoordinates(RelAbsVector(0,0), RelAbsVector(0,50))
                    renderPoint2 = polygon.createPoint()
                    renderPoint2.setCoordinates(RelAbsVector(0,100), RelAbsVector(0,50))
                elif node.shape_index == 4: #triangle(3)
                    polygon = style.getGroup().createPolygon()
                    renderPoint1 = polygon.createPoint()
                    renderPoint1.setCoordinates(RelAbsVector(0,100), RelAbsVector(0,50))
                    renderPoint2 = polygon.createPoint()
                    renderPoint2.setCoordinates(RelAbsVector(0,25), RelAbsVector(0,7))
                    renderPoint3 = polygon.createPoint()
                    renderPoint3.setCoordinates(RelAbsVector(0,25), RelAbsVector(0,86))
                else: #rectangle shape_index = 0/text-only 5/demo-combo 7/others as default (rectangle)
                    rectangle = style.getGroup().createRectangle()
                    rectangle.setCoordinatesAndSize(RelAbsVector(0,0),RelAbsVector(0,0),RelAbsVector(0,0),RelAbsVector(0,100),RelAbsVector(0,100))
               
                style = rInfo.createStyle("textStyle")
                style.getGroup().setStroke("text_line_color" + "_" + spec_id)
                style.getGroup().setStrokeWidth(1.)
                style.getGroup().setFontSize(RelAbsVector(text_font_size,0))
                style.addType("TEXTGLYPH")
                style.addId(spec_id)

            if numReactions != 0:
                for i in range(len(allReactions)):
                    rxn_id = allReactions[i].id
                    reaction_fill_color     = allReactions[i].fill_color
                    reaction_fill_color_str = '#%02x%02x%02x' % (reaction_fill_color.r,reaction_fill_color.g,reaction_fill_color.b)           
                    reaction_line_thickness = allReactions[i].line_thickness
                    reaction_id = allReactions[i].id

                    color = rInfo.createColorDefinition()
                    color.setId("reaction_fill_color" + "_" + rxn_id)
                    color.setColorValue(reaction_fill_color_str)

                    style = rInfo.createStyle("reactionStyle" + "_" + rxn_id)
                    style.getGroup().setStroke("reaction_fill_color" + "_" + rxn_id)
                    style.getGroup().setStrokeWidth(reaction_line_thickness)
                    style.addType("REACTIONGLYPH SPECIESREFERENCEGLYPH")
                    style.addId(reaction_id)
            
            sbmlStr_layout_render = writeSBMLToString(doc)
            return sbmlStr_layout_render

    def Save(self, evt):
        """
        Handler for the "Save" button.
        Save the SBML string to a file.
        """
        self.dirname=""  #set directory name to blank 
        dlg = wx.FileDialog(self.window, "Save As", self.dirname, wildcard="SBML files (*.xml)|*.xml", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            # Grab the content to be saved
            itcontains = self.SBMLText.GetValue()
            # Open the file for write, write, close
            self.filename=dlg.GetFilename()
            self.dirname=dlg.GetDirectory()
            filehandle=open(os.path.join(self.dirname, self.filename),'w')
            filehandle.write(itcontains)
            filehandle.close()
        # Get rid of the dialog to keep things tidy
        dlg.Destroy()



