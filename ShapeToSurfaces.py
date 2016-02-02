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
shapeToSurfacePanel =None

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
        cmdDef.toolClipFilename = os.path.join(resourceDir,'FATHOM_tool_tip.png')
        onCommandCreated = ShapeToSurfaceCommandCreatedHandler() #Create UI
        cmdDef.commandCreated.add(onCommandCreated)
        handlers.append(onCommandCreated)


        toolbarControls = ui.allToolbarPanels.itemById('SolidMakePanel').controls

        global toolbarControls


        toolbarControl = toolbarControls.itemById(commandId)
        if toolbarControl:
            toolbarControl.deleteMe()

        #toolbarControl = toolbarControls.addCommand(commandDefinition, toolbarControls.item(0).id)     
        #toolbarControl.isVisible = True


        # Add the SmartQuote command to the Make panel
        #toolbarControl = toolbarControls.addCommand(cmdDef, toolbarControls.item(1).id)     
        #toolbarControl.isVisible = True

        inputs = adsk.core.NamedValues.create()
        cmdDef.execute(inputs)



        # prevent this module from being terminate when the script returns, because we are waiting for event handlers to fire
        adsk.autoTerminate(False)

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class ShapeToSurfaceCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):    
    def __init__(self):
        super().__init__()        
    def notify(self, args):
        try:
            cmd = args.command
            onExecute = ShapeToSurfaceCommandExecuteHandler()
            cmd.execute.add(onExecute)
            onDestroy = ShapeToSurfaceCommandDestroyHandler()
            cmd.destroy.add(onDestroy)
            onValidateInputs = ShapeToSurfaceCommandValidateInputsHandler()
            cmd.validateInputs.add(onValidateInputs)
            
            # keep the handler referenced beyond this function
            handlers.append(onExecute)
            handlers.append(onDestroy)
            handlers.append(onValidateInputs)

            # Define the inputs.
            inputs = cmd.commandInputs

            initialVal = adsk.core.ValueInput.createByReal(.0254)
            inputs.addValueInput('layerHeight', 'Layer Height', 'mm' , initialVal)

            inputs.addStringValueInput('numContours', 'Number of Contours', '3')

            initialVal4 = adsk.core.ValueInput.createByReal(.0508)
            inputs.addValueInput('contWidth', 'Contour Width', 'mm' , initialVal4)

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class ShapeToSurfaceCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            unitsMgr = app.activeProduct.unitsManager
            command = args.firingEvent.sender
            inputs = command.commandInputs

            # We need access to the inputs within a command during the execute.
            layerHeightInput = inputs.itemById('layerHeight')
            numContoursInput = inputs.itemById('numContours')
            contWidthInput = inputs.itemById('contWidth')

            #In case no value was entered
            layerHeight = .0254
            numContours = 3
            contWidth = .0508

            if not layerHeightInput or not numContoursInput or not contWidthInput:
                ui.messageBox("One of the inputs don't exist.")
            else:
                layerHeight = unitsMgr.evaluateExpression(layerHeightInput.expression, "mm")
                contWidth = unitsMgr.evaluateExpression(contWidthInput.expression, "mm")
    
                if numContoursInput.value != '':
                    numContours = int(numContoursInput.value)

            createPlane(layerHeight, numContours, contWidth)

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def createPlane(layerHeight, numContours, contWidth):
    activeDoc = adsk.core.Application.get().activeDocument
    design = activeDoc.design       
    rootComp = design.rootComponent     
    rootComp.occurrences.addNewComponent (adsk.core.Matrix3D.create()).component.name=("extrusions")

    modelMinZ=rootComp.boundingBox.minPoint.z
    modelMaxZ=rootComp.boundingBox.maxPoint.z

    planes=rootComp.constructionPlanes
    planeInOff=planes.createInput()

    planeInOff.setByOffset(rootComp.xYConstructionPlane,adsk.core.ValueInput.createByReal(modelMinZ))
    planeMin=planes.add(planeInOff)
    planeMin.isLightBulbOn=False
    planeHeight = modelMinZ

    while planeHeight  <=  modelMaxZ:
        planeInput = planes.createInput()
        offsetValue = adsk.core.ValueInput.createByReal(planeHeight)
        planeInput.setByOffset(rootComp.xYConstructionPlane, offsetValue)
        planeOne = planes.add(planeInput)
        projectToPlane(planeOne,contWidth,numContours,layerHeight, planeHeight)
        planeHeight+= layerHeight

        
    return

def projectToPlane(plane, contWidth, numContours, layerHeight, planeHeight):
    #First we need to create a sketch
    activeDoc = adsk.core.Application.get().activeDocument
    design = activeDoc.design       
    rootComp = design.rootComponent
    sketches= rootComp.sketches
    sketch = sketches.add(plane)
    bodies = rootComp.bRepBodies
    for body in bodies:
        bodyMaxZ = body.boundingBox.maxPoint.z
        bodyMinZ = body.boundingBox.minPoint.z

        if  bodyMaxZ  >=  planeHeight  and  bodyMinZ < planeHeight:
            sketch.projectCutEdges(body)

    extrudeSurface(layerHeight,sketch, numContours, contWidth)
    design.activateRootComponent()
    return


def extrudeSurface(layerHeight,sketch, numContours, contWidth):
    # Fetch the root component and some of the features we'll be using
    #rootComp=adsk.core.Application.get().activeDocument.design.rootComponent
    activeDoc = adsk.core.Application.get().activeDocument
    design = activeDoc.design       
    rootComp = design.rootComponent
    features= rootComp.features

    #use the new componentas the root comp
    extrudesComp = rootComp.occurrences.itemByName("extrusions:1").component
    extrudes = extrudesComp.features.extrudeFeatures
    offsets = extrudesComp.features.offsetFeatures #this should be offsetComp but it crashers
    
    distance = adsk.core.ValueInput.createByReal(layerHeight-.001)
         
    # make an object collection containing all of the curves/lines in the sketch
    curveCollection = adsk.core.ObjectCollection.create()
    curves=sketch.sketchCurves
    for curve in curves:
        curveCollection.add(curve)
               
    # build the collection of open profiles
    while (curveCollection.count > 0):
        # Add the first curve and any connected curves to the collection of channel profiles
        curve = curveCollection.item(0) 
        if curve.isConstruction:
            curveCollection.removeByIndex(0)
        else:
            profileCollection = adsk.core.ObjectCollection.create()
            profileCollection.add(rootComp.createOpenProfile(curve))
            for connectedCurve in sketch.findConnectedCurves(curve):
                curveCollection.removeByItem(connectedCurve)
        
            extrudeInput = extrudes.createInput(profileCollection, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            extrudeInput.isSolid = False
        
            extrudeInput.setDistanceExtent(False, distance)
            extrude = extrudes.add(extrudeInput)

            #Creating offsets
           
            body = extrude.bodies[0]
            offsetSurfaces(body,numContours,contWidth)
           

def offsetSurfaces (body, numContours, contWidth):
    activeDoc = adsk.core.Application.get().activeDocument
    design = activeDoc.design       
    rootComp = design.rootComponent
    features= rootComp.features

    #use the new componentas the root comp
    extrudesComp = rootComp.occurrences.itemByName("extrusions:1").component
    extrudes = extrudesComp.features.extrudeFeatures
    offsets = extrudesComp.features.offsetFeatures #this should be offsetComp but it crashers    
    for contCounter in range(1,numContours):
        rootComp.occurrences.itemByName("extrusions:1").activate()
        inputEntities = adsk.core.ObjectCollection.create()
        inputEntities.add(body)
        #we multiply contWidth by (-1) to make the offset to the inside of the shape
        distanceOffset = adsk.core.ValueInput.createByReal(-1*contWidth*contCounter)
        offsetInput = offsets.createInput(inputEntities, distanceOffset, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        #Check if the offset is valid (it might be too small to exist, in that case ignore it )
        try:
            offsets.add(offsetInput)
        except:
            #errorMessage = 'Failed:\n{}'.format(traceback.format_exc())
            #Just call any other API method in your except: block to reset the last error
            adsk.core.ObjectCollection.create()
            
            


class ShapeToSurfaceCommandDestroyHandler(adsk.core.CommandEventHandler):
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


class ShapeToSurfaceCommandValidateInputsHandler(adsk.core.ValidateInputsEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            command = args.firingEvent.sender
            inputs = command.commandInputs
            
            layerHeightInput = inputs.itemById('layerHeight')
            numContoursInput = inputs.itemById('numContours')
            contWidthInput = inputs.itemById('contWidth')
            
            unitsMgr = app.activeProduct.unitsManager
            layerHeight = unitsMgr.evaluateExpression(layerHeightInput.expression, "mm")
            contWidth = unitsMgr.evaluateExpression(contWidthInput.expression, "mm")
            numContours = 0
            if numContoursInput.value.isdigit():
                numContours = int(numContoursInput.value)
                
            if numContours < 2 or layerHeight <= 0 or contWidth <= 0:
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