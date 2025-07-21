import adsk.core
import adsk.fusion
import math
import os
import json
import time
from ...lib import fusionAddInUtils as futil

app = adsk.core.Application.get()
ui = app.userInterface
skipValidate = False


class MarbleRunLogic():
    def __init__(self, des: adsk.fusion.Design):
        # Read the cached values, if they exist.
        settings = None
        settingAttribute = des.attributes.itemByName('MarbleRun', 'settings')
        if settingAttribute is not None:
            jsonSettings = settingAttribute.value
            settings = json.loads(jsonSettings)              

        defaultUnits = des.unitsManager.defaultLengthUnits
            
        # Determine whether to use inches or millimeters as the intial default.
        if defaultUnits == 'in' or defaultUnits == 'ft':
            self.units = 'in'
        else:
            self.units = 'mm'
        
        # Define the default for each value and then check to see if there
        # were cached settings and override the default if a setting exists.
        self.diameter = '1.3'
        if settings:
            self.diameter = settings['Diameter']

        self.ignoreArcCenters = True
        if settings:
            self.ignoreArcCenters = settings['IgnoreArcCenters']


    def CreateCommandInputs(self, inputs: adsk.core.CommandInputs):
        global skipValidate
        skipValidate = True

        # Create the command inputs to define the contents of the command dialog.
        selection_input = inputs.addSelectionInput('selection_input', 'Selection', 'Select Sketch Geometry')
        selection_input.addSelectionFilter('SketchPoints')
        selection_input.addSelectionFilter('SketchCircles')
        selection_input.addSelectionFilter('SketchLines')
        selection_input.addSelectionFilter('SketchCurves')
        selection_input.setSelectionLimits(1, 0)

        self.diameterValueInput = inputs.addValueInput('diameter', 'Diameter', 'mm', adsk.core.ValueInput.createByReal(float(self.diameter)))

        self.ignoreArcCentersValueInput = inputs.addBoolValueInput('ignore_arc_centers', 'Ignore Arc Centers', True, '', self.ignoreArcCenters)
        self.ignoreArcCentersValueInput.tooltip = "Check this to prevent the command dialog from adding spheres to the center points of arcs and circles."


        skipValidate = False

    def HandlePreselection(self, args: adsk.core.CommandEventArgs):
        selection = args.selection
        entity = selection.entity
        futil.log(f'entity is of type {entity.objectType}')
        
        # Ignore the entity if it's construction geometry
        if hasattr(entity, 'isConstruction') and entity.isConstruction: # the first condition prevents an error if the entity does not have a 'isConstruction' attribute
            args.isSelectable = False
            return
        
        # If the "Ignore Arc Centers" checkbox is checked, ignore arc and circle center points.
        if entity.objectType == adsk.fusion.SketchPoint.classType():
            sketch_point = entity
            sketch = sketch_point.parentSketch
            if self.ignoreArcCenters and is_arc_center_point(sketch_point, sketch):
                args.isSelectable = False
                return

    def HandleInputsChanged(self, args: adsk.core.InputChangedEventArgs):
        changedInput = args.input
        if not skipValidate:
            self.ignoreArcCenters = self.ignoreArcCentersValueInput.value
                


    def HandleValidateInputs(self, args: adsk.core.ValidateInputsEventArgs):
        pass


    def HandleExecute(self, args: adsk.core.CommandEventArgs):
        inputs = args.command.commandInputs
        selection_input: adsk.core.SelectionCommandInput = inputs.itemById('selection_input')
        ignore_arc_centers = self.ignoreArcCentersValueInput.value
        num_selections = selection_input.selectionCount
        # msg = f'You have {num_selections} selections selected.'
        # ui.messageBox(msg)
        stored_point_entities = []
        stored_curve_entities = []
        for i in range(num_selections):
            selected_entity = selection_input.selection(i).entity
            if selected_entity.objectType == adsk.fusion.SketchPoint.classType():
                stored_point_entities.append(selected_entity)
            else:
                stored_curve_entities.append(selected_entity)
        
        des = adsk.fusion.Design.cast(app.activeProduct)
        comp = des.activeComponent
        features = comp.features

        inputs = args.command.commandInputs
        diameter = inputs.itemById('diameter').value # this is a float
        diameter_text = inputs.itemById('diameter').expression # this extracts exactly what the user typed as a string. Works for both numbers and user parameter names.

        #  Create all pipes
        isFirstPipe = True
        firstPipe = None
        for entity in stored_curve_entities:
            path = adsk.fusion.Path.create(entity, adsk.fusion.ChainedCurveOptions.noChainedCurves)
            sectionSize = diameter_text
            pipe = create_pipe(comp, path, sectionSize)
            if isFirstPipe:
                firstPipe = pipe
                isFirstPipe = False
        firstTimelineFeature = firstPipe

        # Create a sphere
        sketches = comp.sketches
        xyPlane = comp.xYConstructionPlane
        sketch = sketches.add(xyPlane)
        if not firstTimelineFeature:
            firstTimelineFeature = sketch
        arcs = sketch.sketchCurves.sketchArcs
        lines = sketch.sketchCurves.sketchLines
        
        center = adsk.core.Point3D.create(0, 0, 0)
        startPoint = adsk.core.Point3D.create(0, diameter/2.0, 0)
        endPoint = adsk.core.Point3D.create(0, -1*diameter/2.0, 0)
        diameterLine = lines.addByTwoPoints(startPoint, endPoint)
        arc = arcs.addByCenterStartEnd(center, diameterLine.startSketchPoint, diameterLine.endSketchPoint) # using the line's endpoint attributes joins the line to the arc

        textPoint: adsk.core.Point3D = arc.centerSketchPoint.geometry.copy()
        textPoint.translateBy(adsk.core.Vector3D.create(0.25,0.25,0))
        dimensions: adsk.fusion.SketchDimensions = sketch.sketchDimensions
        diameterDim: adsk.fusion.SketchDiameterDimension = dimensions.addDiameterDimension(arc, textPoint, True)
        modelPrm: adsk.fusion.ModelParameter = diameterDim.parameter
        # modelPrm.expression = diam_param.name
        modelPrm.expression = diameter_text

        origin_point = sketch.originPoint
        circle_center = arc.centerSketchPoint
        constraints = sketch.geometricConstraints
        circle_coincident_constraint = constraints.addCoincident(circle_center, origin_point)
        line_coincident_constraint = constraints.addCoincident(circle_center, diameterLine)
        vertical_constraint = constraints.addVertical(diameterLine)

        prof = sketch.profiles.item(0)
        revolves = comp.features.revolveFeatures
        revInput = revolves.createInput(prof, diameterLine, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        revInput.setAngleExtent(False, adsk.core.ValueInput.createByReal(math.pi * 2))
        sphere = revolves.add(revInput)

        fromPoint = des.rootComponent.originConstructionPoint

        #  Create all spheres
        for entity in stored_point_entities:
            toPoint = entity
            create_sphere(comp, sphere, fromPoint, toPoint)

        # Parametrically remove the reference sphere at the origin
        removeFeatures = features.removeFeatures
        removeSphere = removeFeatures.add(sphere.bodies[0]) # sphere.bodies.item(0) also seems to work

        # Put the timeline features into a group
        timelineGroups = des.timeline.timelineGroups
        timelineStartIndex = firstTimelineFeature.timelineObject.index
        timelineEndIndex = removeSphere.timelineObject.index
        timelineGroup = timelineGroups.add(timelineStartIndex, timelineEndIndex)
        timelineGroup.name = 'Ball Track Cutter'

        
        # Save the current values as attributes.
        settings = {'Diameter': str(self.diameterValueInput.value),
                    'IgnoreArcCenters': self.ignoreArcCentersValueInput.value}

        jsonSettings = json.dumps(settings)

        attribs = des.attributes
        attribs.add('MarbleRun', 'settings', jsonSettings)


def is_arc_center_point(sketch_point, sketch):
   """Check if a sketch point is the center of any arc or circle in its sketch"""
   
   # Get all arcs in the sketch
   arcs = sketch.sketchCurves.sketchArcs
   circles = sketch.sketchCurves.sketchCircles

   for arc in arcs:
       if arc.centerSketchPoint == sketch_point:
           return True
   for circle in circles:
       if circle.centerSketchPoint == sketch_point:
           return True
   
   return False


def create_pipe(component, path, sectionSize: str):
    """Create pipe feature along the sketch curve or line"""
    features = component.features
    pipes = features.pipeFeatures
    pipe_input = pipes.createInput(path, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    pipe_input.sectionSize = adsk.core.ValueInput.createByReal(0.05) # Start with a small value to avoid pipe generation errors due to small sketch curve radii
    pipe = pipes.add(pipe_input)
    pipe.sectionSize.expression = sectionSize # must set this equal to a string
    return pipe


def create_sphere(component, sphere, fromPoint, toPoint):
    # Copy the sphere
    copyPasteFeatures = component.features.copyPasteBodies
    sphereCopy = copyPasteFeatures.add(sphere.bodies.item(0))

    # Move the sphere to the user selected point.
    moveFeatures = component.features.moveFeatures
    
    bodyToMove = sphereCopy.bodies.item(0)
    objectCollection = adsk.core.ObjectCollection.create()
    objectCollection.add(bodyToMove)
    
    moveInput = moveFeatures.createInput2(objectCollection)

    moveInput.defineAsPointToPoint(fromPoint, toPoint)
    moveFeature = moveFeatures.add(moveInput)
    return sphereCopy

