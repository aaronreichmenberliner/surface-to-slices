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
        commandId = 'SpurGear'
        commandName = 'Convert Model to Surfaces'
        commandDescription = 'Conver Model to Surfaces for 3D Printing'
        cmdDef = ui.commandDefinitions.itemById(commandId)
        if not cmdDef:
            resourceDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources') # absolute resource file path is specified
            cmdDef = ui.commandDefinitions.addButtonDefinition(commandId, commandName, commandDescription, resourceDir)

        onCommandCreated = SpurGearCommandCreatedHandler() #Create UI
        cmdDef.commandCreated.add(onCommandCreated)
        # keep the handler referenced beyond this function
        handlers.append(onCommandCreated)

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

            inputs.addStringValueInput('numLayers', 'Number of Layers', '5')
            inputs.addStringValueInput('numContours', 'Number of Contours', '3')

            initialVal4 = adsk.core.ValueInput.createByReal(.020)
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
    #features = rootComp.features        
    flowSketch = rootComp.sketches.itemByName("Sketch1")

    for planeCounter in range (0,numLayers):
        planes = rootComp.constructionPlanes
        planeInput = planes.createInput()
        offsetValue = adsk.core.ValueInput.createByReal(planeCounter*layerHeight)
        planeInput.setByOffset(flowSketch, offsetValue)
        planeOne = planes.add(planeInput)
        projectToPlane(planeOne,contWidth,numContours)
    return

def projectToPlane(plane, contWidth, numContours):
    #First we need to create a sketch
    activeDoc = adsk.core.Application.get().activeDocument
    design = activeDoc.design       
    rootComp = design.rootComponent
    sketches= rootComp.sketches
    sketch = sketches.add(plane)
    bodies = rootComp.bRepBodies
    #now we can intersect the bodies with the sletch
    for body in bodies:
        sketch.projectCutEdges(body)
        offsetCurves(sketch,contWidth, numContours)
    return

def offsetCurves(sketch, contWidth, numContours):
    activeDoc= adsk.core.Application.get().activeDocument
    design = activeDoc.design    
    rootComp = design.rootComponent
     
    # make an object collection containing all of the curves/lines in the sketch
    #curveCollection = adsk.core.ObjectCollection.create()
    lines= sketch.sketchCurves.sketchLines
    app = adsk.core.Application.get()
    ui  = app.userInterface
    #newLine= lines.addByTwoPoints(adsk.core.Point3D.create(0, 0, 0), adsk.core.Point3D.create(3, 1, 0))
    newRec= lines.addThreePointRectangle(adsk.core.Point3D.create(8, 0, 0), adsk.core.Point3D.create(11, 1, 0), adsk.core.Point3D.create(9, 3, 0))
    curves = sketch.findConnectedCurves(newRec.item(1))
    #ui.messageBox(str(curves.classType))

    #for curve in curves:
    #    curveCollection.add(curve)
        #ui.messageBox('Hello script')
    dirPoint = adsk.core.Point3D.create(0, 0.5, 0)
    offsets = sketch.offset(curves, dirPoint ,0.5)
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
