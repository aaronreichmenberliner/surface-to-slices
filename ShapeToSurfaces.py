#Author-Autodesk Inc.
#Description-Create a spur gear.

import adsk.core, adsk.fusion, traceback
import os, math

# global set of event handlers to keep them referenced for the duration of the command
handlers = []

app = adsk.core.Application.get()
if app:
    ui = app.userInterface

newComp = None

def createNewComponent():
    # Get the active design.
    product = app.activeProduct
    design = adsk.fusion.Design.cast(product)
    rootComp = design.rootComponent
    allOccs = rootComp.occurrences
    newOcc = allOccs.addNewComponent(adsk.core.Matrix3D.create())
    return newOcc.component


def run(context):
    try:
        commandId = 'ShapeToSurfaces'
        commandName = 'Convert Solid Model to Layer Surfaces'
        commandDescription = 'Conver Solid Model to Layer Surfaces for 3D Printing'
        resourceDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources') # absolute resource file path is specified
        global cmdDef
        cmdDef = ui.commandDefinitions.itemById(commandId)
        
        if cmdDef:
            cmdDef.deleteMe()

        cmdDef = ui.commandDefinitions.addButtonDefinition(commandId, commandName, '', os.path.join(resourceDir,'ShapeToSurfaces'))
        onCommandCreated = SpurGearCommandCreatedHandler() #Create UI
        cmdDef.commandCreated.add(onCommandCreated)
        # keep the handler referenced beyond this function
        handlers.append(onCommandCreated)

        toolbarControls = ui.allToolbarPanels.itemById('SolidMakePanel').controls

        global toolbarControls
        toolbarControls = toolbarControls.itemById(commandId)
        if toolbarControls:
            toolbarControls.deleteMe()
        #toolbarControl = toolbarControls.addCommand(cmdDef, toolbarControls.item(1).id)     
        #toolbarControl.isVisible = True

        inputs = adsk.core.NamedValues.create()
        cmdDef.execute(inputs)

        # prevent this module from being terminate when the script returns, because we are waiting for event handlers to fire
        adsk.autoTerminate(False)

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

class SpurGearCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):    
    def __init__(self):
        super().__init__()        
    def notify(self, args):
        try:
            cmd = args.command
            onExecute = SpurGearCommandExecuteHandler()
            cmd.execute.add(onExecute)
            onDestroy = SpurGearCommandDestroyHandler()
            cmd.destroy.add(onDestroy)
            onValidateInputs = SpurGearCommandValidateInputsHandler()
            cmd.validateInputs.add(onValidateInputs)
            
            # keep the handler referenced beyond this function
            handlers.append(onExecute)
            handlers.append(onDestroy)
            handlers.append(onValidateInputs)

            # Define the inputs.
            inputs = cmd.commandInputs

            initialVal = adsk.core.ValueInput.createByReal(.0254)
            inputs.addValueInput('layerHeight', 'Layer Height', 'mm' , initialVal)

            inputs.addStringValueInput('numLayers', 'Number of Layers', '10')
            inputs.addStringValueInput('numContours', 'Number of Contours', '3')

            initialVal4 = adsk.core.ValueInput.createByReal(.0508)
            inputs.addValueInput('contWidth', 'Contour Width', 'mm' , initialVal4)

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class SpurGearCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            unitsMgr = app.activeProduct.unitsManager
            command = args.firingEvent.sender
            inputs = command.commandInputs

            # We need access to the inputs within a command during the execute.
            layerHeightInput = inputs.itemById('layerHeight')
            numLayersInput = inputs.itemById('numLayers')
            numContoursInput = inputs.itemById('numContours')
            contWidthInput = inputs.itemById('contWidth')

            #In case no value was entered
            layerHeight = .0254
            numLayers = 10
            numContours = 3
            contWidth = .0508

            if not layerHeightInput or not numLayersInput or not numContoursInput or not contWidthInput:
                ui.messageBox("One of the inputs don't exist.")
            else:
                layerHeight = unitsMgr.evaluateExpression(layerHeightInput.expression, "mm")
                contWidth = unitsMgr.evaluateExpression(contWidthInput.expression, "mm")
                numLayers= int(numLayersInput.value)
    
                if numContoursInput.value != '':
                    numContours = int(numContoursInput.value)

            createPlane(layerHeight, numContours, numLayers, contWidth)

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def createPlane(layerHeight, numContours, numLayers, contWidth):
    activeDoc = adsk.core.Application.get().activeDocument
    design = activeDoc.design       
    rootComp = design.rootComponent     
    flowSketch = rootComp.sketches.itemByName("Sketch1")

    for planeCounter in range (0,numLayers):
        planes = rootComp.constructionPlanes
        planeInput = planes.createInput()
        planeHeight =  planeCounter*layerHeight
        offsetValue = adsk.core.ValueInput.createByReal(planeHeight)
        planeInput.setByOffset(flowSketch, offsetValue)
        planeOne = planes.add(planeInput)
        projectToPlane(planeOne,contWidth,numContours,layerHeight, planeHeight)
    #offsetCurves(contWidth, numContours)
    return

def projectToPlane(plane, contWidth, numContours, layerHeight, planeHeight):
    #First we need to create a sketch
    activeDoc = adsk.core.Application.get().activeDocument
    design = activeDoc.design       
    rootComp = design.rootComponent
    sketches= rootComp.sketches
    sketch = sketches.add(plane)
    bodies = rootComp.bRepBodies
    #now we can intersect the bodies with the sletch
    for body in bodies:
        bodyZ=body.boundingBox.maxPoint.z
        if bodyZ >= planeHeight:
            sketch.projectCutEdges(body)

    extrudeSurface(layerHeight,sketch)
        #offsetCurves(contWidth, numContours)
    return


def extrudeSurface(layerHeight,sketch):
 # Fetch the root component and some of the features we'll be using
    activeDoc = adsk.core.Application.get().activeDocument
    design = activeDoc.design       
    rootComp = design.rootComponent
    features = rootComp.features
    extrudes = features.extrudeFeatures
        
    #flowSketch = rootComp.sketches.sketch
    distance = adsk.core.ValueInput.createByReal(layerHeight-.001)
    
    # empty collection to hold all the curves we'll be using to make channels
    curveCollection = adsk.core.ObjectCollection.create()
        
    # make an object collection containing all of the curves/lines in the sketch
    #curves = flowSketch.sketchCurves
    curves=sketch.sketchCurves
    for curve in curves:
        curveCollection.add(curve)
    #comment(curves.count)
        
               
    # build the collection of open profiles
    while (curveCollection.count > 0):
        # Add the first curve and any connected curves to the collection of channel profiles
        curve = curveCollection.item(0) 
        if curve.isConstruction:
            # if it's Construction geometry, then delete and don't process
            curveCollection.removeByIndex(0)
        else:
            profileCollection = adsk.core.ObjectCollection.create()

            # for non-construction curves, add the open profile consisting of all the connected curves
            # to the collection of profiles we'll be extruding
            profileCollection.add(rootComp.createOpenProfile(curve))
            
            # remove all the connected curves (which includes the original) from the curve collection
            # so we don't add duplicates to the profile collection
            for connectedCurve in sketch.findConnectedCurves(curve):
                curveCollection.removeByItem(connectedCurve)
        
            extrudeInput = extrudes.createInput(profileCollection, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            extrudeInput.isSolid = False
        
            extrudeInput.setDistanceExtent(False, distance)
            extrude = extrudes.add(extrudeInput)


def offsetCurves(contWidth, numContours):
    activeDoc= adsk.core.Application.get().activeDocument
    #rootComp=activeDoc.design.rootComponent
    sketches=activeDoc.design.rootComponent.sketches   
    sketch = sketches.itemByName("Sketch1")

    lines= sketch.sketchCurves.sketchLines
    curves = sketch.findConnectedCurves(lines.item(0))
    #distance = adsk.core.ValueInput.createByReal(contWidth)

    #   comment(lines.count)

    dirPoint = adsk.core.Point3D.create(9999, 9999, 0) #far away to make sure it is outside all bodies
    
    for offsetCounter in range (1,numContours): 
        sketch.offset(curves, dirPoint, offsetCounter*contWidth)

    return

class SpurGearCommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            # when the command is done, terminate the script
            # this will release all globals which will remove all event handlers
            adsk.terminate()
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class SpurGearCommandValidateInputsHandler(adsk.core.ValidateInputsEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            command = args.firingEvent.sender
            inputs = command.commandInputs
            
            layerHeightInput = inputs.itemById('layerHeight')
            numLayersInput = inputs.itemById('numLayers')
            numContoursInput = inputs.itemById('numContours')
            contWidthInput = inputs.itemById('contWidth')
            
            unitsMgr = app.activeProduct.unitsManager
            layerHeight = unitsMgr.evaluateExpression(layerHeightInput.expression, "mm")
            #numLayers = unitsMgr.evaluateExpression(numLayersInput.expression, "deg")
            numLayers=0
            contWidth = unitsMgr.evaluateExpression(contWidthInput.expression, "mm")
            numContours = 0
            if numContoursInput.value.isdigit():
                numContours = int(numContoursInput.value)
                
            if numContours < 2 or layerHeight <= 0 or contWidth <= 0 or numLayers < 0:
                args.areInputsValid = False
            else:
                args.areInputsValid = True
            
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def comment(inputComment):
    app = adsk.core.Application.get()
    ui  = app.userInterface
    ui.messageBox(str(inputComment))
    return