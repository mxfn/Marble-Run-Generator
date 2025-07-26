import adsk.core
import adsk.fusion
from . import path_generator
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

        # self.ignoreArcCenters = True
        # if settings:
        #     self.ignoreArcCenters = settings['IgnoreArcCenters']


    def CreateCommandInputs(self, inputs: adsk.core.CommandInputs):
        global skipValidate
        skipValidate = True

        # Create the command inputs to define the contents of the command dialog.
        self.widthValueInput = inputs.addIntegerSliderCommandInput('num_x_cells', 'Width', 2, 15, False)
        self.widthValueInput.tooltip = "Number of cells in the X direction"
        self.widthValueInput.valueOne = 5 # set default value
        self.depthValueInput = inputs.addIntegerSliderCommandInput('num_y_cells', 'Depth', 2, 15, False)
        self.depthValueInput.tooltip = "Number of cells in the Y direction"
        self.depthValueInput.valueOne = 5 # set default value

        self.diameterValueInput = inputs.addValueInput('diameter', 'Marble Diameter', 'mm', adsk.core.ValueInput.createByReal(float(self.diameter)))
        self.clearanceValueInput = inputs.addValueInput('clearance', 'Clearance', 'mm', adsk.core.ValueInput.createByReal(0.015))
        self.clearanceValueInput.tooltip = "Clearance between the marble and the track"

        self.slopeValueInput = inputs.addValueInput('slope', 'Slope', '', adsk.core.ValueInput.createByReal(0.09))
        slope = self.slopeValueInput.value
        angle = abs(math.degrees(math.atan2(slope, 1.0)))
        angle_text = f'{angle:.2f} deg' # display angle to two decimal places
        self.angleTextInput = inputs.addTextBoxCommandInput('angle', 'Angle', angle_text, 1, True)

        self.errorMessageTextInput = inputs.addTextBoxCommandInput('errMessage', '', '', 2, True)
        self.errorMessageTextInput.isFullWidth = True

        skipValidate = False

    def HandleInputsChanged(self, args: adsk.core.InputChangedEventArgs):
        des = adsk.fusion.Design.cast(app.activeProduct)
        changedInput = args.input
        if not skipValidate:
            # self.ignoreArcCenters = self.ignoreArcCentersValueInput.value
            if changedInput.id == 'slope':
                slope = self.slopeValueInput.value
                angle = abs(math.degrees(math.atan2(slope, 1.0)))
                angle_text = f'{angle:.2f} deg' # display angle to two decimal places
                self.angleTextInput.text = angle_text
                

    def HandleValidateInputs(self, args: adsk.core.ValidateInputsEventArgs):
        if not skipValidate:
            self.errorMessageTextInput.text = ''
            # Make sure the slope is greater than 0
            if self.slopeValueInput.value <= 0.0:
                self.errorMessageTextInput.text = 'The slope must be greater than 0'
                args.areInputsValid = False
                return

    def HandleExecute(self, args: adsk.core.CommandEventArgs):
        inputs = args.command.commandInputs
        
        des = adsk.fusion.Design.cast(app.activeProduct)
        comp = des.activeComponent
        features = comp.features
        extrudes = features.extrudeFeatures
        pipes = features.pipeFeatures
        revolves = features.revolveFeatures
        copy_pastes = features.copyPasteBodies
        moves = features.moveFeatures
        mirrors = features.mirrorFeatures
        combines = features.combineFeatures
        sketches = comp.sketches
        xyPlane = comp.xYConstructionPlane
        xzPlane = comp.xZConstructionPlane
        yzPlane = comp.yZConstructionPlane
        zAxis = comp.zConstructionAxis

        num_x_cells = inputs.itemById('num_x_cells').valueOne # int
        num_y_cells = inputs.itemById('num_y_cells').valueOne # int
        num_x_cells_text = inputs.itemById('num_x_cells').expressionOne # Str
        num_y_cells_text = inputs.itemById('num_y_cells').expressionOne # Str

        slope = inputs.itemById('slope').value
        slope_text = inputs.itemById('slope').expression
        # slope = 0.09

        ball_diameter = inputs.itemById('diameter').value # this is a float
        ball_diameter_text = inputs.itemById('diameter').expression # this extracts exactly what the user typed as a string. Works for both numbers and user parameter names.

        clearance = inputs.itemById('clearance').value
        clearance_text = inputs.itemById('clearance').expression

        diameter = ball_diameter + 2*clearance # float
        diameter_text = f'({ball_diameter_text} + 2 * {clearance_text})' # String

        # Straight track sketch
        straight_track_sketch = sketches.add(xzPlane)
        straight_track_sketch.name = 'Straight Track'
        lines = straight_track_sketch.sketchCurves.sketchLines
        points = straight_track_sketch.sketchPoints
        origin_point = straight_track_sketch.originPoint
        constraints = straight_track_sketch.geometricConstraints
        dimensions = straight_track_sketch.sketchDimensions

        # Create ball path line
        startPoint = adsk.core.Point3D.create(-1*diameter/2-0.5, -1*slope*(diameter/2+0.5), 0)
        endPoint = adsk.core.Point3D.create(diameter/2+0.5, slope*(diameter/2+0.5), 0)
        # point = points.add(startPoint)
        ball_path_line = lines.addByTwoPoints(startPoint, endPoint)
        constraints.addMidPoint(origin_point, ball_path_line)

        # Create the top line
        # startPointX = ball_path_line.startSketchPoint.geometry.copy().x + 0.5
        # startPoint = adsk.core.Point3D.create(startPointX, 1.0, 0)
        # endPointX = ball_path_line.endSketchPoint.geometry.copy().x - 0.5
        # endPoint = adsk.core.Point3D.create(endPointX, 1.0, 0)
        startPoint = adsk.core.Point3D.create(-1*diameter/2, 1, 0)
        endPoint = adsk.core.Point3D.create(diameter/2, 1+diameter*slope, 0)
        top_line = lines.addByTwoPoints(startPoint, endPoint)

        # Add dimensions to the top line
        textPoint = top_line.startSketchPoint.geometry.copy()
        textPoint.translateBy(adsk.core.Vector3D.create(-0.25,0.25,0))
        top_line_v_dim = dimensions.addDistanceDimension(top_line.startSketchPoint, top_line.endSketchPoint, adsk.fusion.DimensionOrientations.VerticalDimensionOrientation, textPoint)
        # top_line_v_dim.parameter.expression = f'{diameter} cm * 0.09'
        top_line_v_dim.parameter.expression = f'{diameter_text} * {slope_text}'
        textPoint = top_line.geometry.evaluator.getPointAtParameter(0.5)[1].copy()
        textPoint.translateBy(adsk.core.Vector3D.create(0,0.25,0))
        top_line_h_dim = dimensions.addDistanceDimension(top_line.startSketchPoint, top_line.endSketchPoint, adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation, textPoint)
        top_line_h_dim.parameter.expression = f'{diameter_text}'

        # Create the left vertical line
        startPointCopy = top_line.startSketchPoint.geometry.copy()
        endPoint = adsk.core.Point3D.create(startPointCopy.x, startPointCopy.y+1, 0)
        left_line = lines.addByTwoPoints(top_line.startSketchPoint, endPoint)
        constraints.addVertical(left_line)

        # Create the right vertical line
        endPointCopy = top_line.endSketchPoint.geometry.copy()
        endPoint = adsk.core.Point3D.create(endPointCopy.x, endPointCopy.y+1, 0)
        right_line = lines.addByTwoPoints(top_line.endSketchPoint, endPoint)
        constraints.addVertical(right_line)

        # Create the bottom line
        bottom_line = lines.addByTwoPoints(left_line.endSketchPoint, right_line.endSketchPoint)

        # Add parallel constraints with the top line
        constraints.addParallel(top_line, ball_path_line)
        constraints.addParallel(top_line, bottom_line)

        # Add dimensions
        # left margin
        textPoint = ball_path_line.startSketchPoint.geometry.copy()
        textPoint.translateBy(adsk.core.Vector3D.create(0.25, -0.1, 0))
        left_margin_dim = dimensions.addOffsetDimension(left_line, ball_path_line.startSketchPoint, textPoint)
        left_margin_dim.parameter.expression = '5 mm'
        # right margin
        textPoint = ball_path_line.endSketchPoint.geometry.copy()
        textPoint.translateBy(adsk.core.Vector3D.create(-0.25, -0.1, 0))
        right_margin_dim = dimensions.addOffsetDimension(right_line, ball_path_line.endSketchPoint, textPoint)
        right_margin_dim.parameter.expression = '5 mm'
        # bottom line
        textPoint = bottom_line.geometry.evaluator.getPointAtParameter(0.5)[1].copy()
        textPoint.translateBy(adsk.core.Vector3D.create(0, -0.1, 0))
        bottom_line_dim = dimensions.addOffsetDimension(ball_path_line, bottom_line, textPoint)
        bottom_line_dim.parameter.expression = f'{diameter_text} / 2 + 2.5 mm'
        # top line
        textPoint = top_line.geometry.evaluator.getPointAtParameter(0.5)[1].copy()
        textPoint.translateBy(adsk.core.Vector3D.create(-0.1, -0.1, 0))
        top_line_dim = dimensions.addOffsetDimension(ball_path_line, top_line, textPoint)
        top_line_dim.parameter.expression = f'{diameter_text} / 4'

        # Extrude sketch profile
        prof = straight_track_sketch.profiles.item(0)
        extrude_input = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        extrude_distance = adsk.core.ValueInput.createByString(diameter_text)
        extrude_input.setSymmetricExtent(extrude_distance, True)
        straight_track_extrude = extrudes.add(extrude_input)
        track_PXPX_body = straight_track_extrude.bodies.item(0)
        track_PXPX_body.name = "Track +X+X"
        
        # Cut ball path using pipe feature
        path = adsk.fusion.Path.create(ball_path_line, adsk.fusion.ChainedCurveOptions.noChainedCurves)
        pipe_input = pipes.createInput(path, adsk.fusion.FeatureOperations.CutFeatureOperation)
        pipe_input.sectionSize = adsk.core.ValueInput.createByReal(diameter)
        pipe = pipes.add(pipe_input)
        pipe.sectionSize.expression = diameter_text # must set this equal to a string

        # Make the track tall so that it easily combines into a 3D printable solid later
        track_footprint_sketch = sketches.add(xyPlane)
        track_footprint_sketch.name = 'Track Footprint'
        lines = track_footprint_sketch.sketchCurves.sketchLines
        points = track_footprint_sketch.sketchPoints
        origin_point = track_footprint_sketch.originPoint
        constraints = track_footprint_sketch.geometricConstraints
        dimensions = track_footprint_sketch.sketchDimensions

        rectangle_point = adsk.core.Point3D.create(-1*diameter/2, diameter/2, 0)
        rec_lines = lines.addCenterPointRectangle(origin_point.geometry.copy(), rectangle_point)
        for i in range(rec_lines.count):
            rec_line = rec_lines.item(i)
            if i%2 == 0:
                constraints.addHorizontal(rec_line)
            else:
                constraints.addVertical(rec_line)
        top_rec_line = rec_lines.item(0)
        right_rec_line = rec_lines.item(1)
        constraints.addEqual(top_rec_line, right_rec_line)
        textPoint = top_rec_line.geometry.evaluator.getPointAtParameter(0.5)[1].copy()
        textPoint.translateBy(adsk.core.Vector3D.create(0, 0.1, 0))
        dimension = dimensions.addDistanceDimension(top_rec_line.startSketchPoint, top_rec_line.endSketchPoint, adsk.fusion.DimensionOrientations.AlignedDimensionOrientation, textPoint)
        dimension.parameter.expression = f'{diameter_text}'
        textPoint = top_rec_line.endSketchPoint.geometry.copy()
        textPoint.translateBy(adsk.core.Vector3D.create(-0.2, 0.2, 0))
        dimension = dimensions.addDistanceDimension(top_rec_line.endSketchPoint, origin_point, adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation, textPoint)
        dimension.parameter.expression = f'{diameter_text} / 2'
        textPoint = top_rec_line.endSketchPoint.geometry.copy()
        textPoint.translateBy(adsk.core.Vector3D.create(0.2, -0.2, 0))
        dimension = dimensions.addDistanceDimension(top_rec_line.endSketchPoint, origin_point, adsk.fusion.DimensionOrientations.VerticalDimensionOrientation, textPoint)
        dimension.parameter.expression = f'{diameter_text} / 2'

        prof = track_footprint_sketch.profiles.item(0)
        extrude_input = extrudes.createInput(prof, adsk.fusion.FeatureOperations.JoinFeatureOperation)
        extrude_offset_text = f'-1 * ({num_x_cells_text} * {num_y_cells_text} * {diameter_text} * {slope_text} + {diameter_text} / 2 + 10 mm)'
        start_offset = adsk.core.ValueInput.createByString(extrude_offset_text)
        extrude_input.startExtent = adsk.fusion.OffsetStartDefinition.create(start_offset)
        # Extract the extrude target face by finding the face created by the bottom line of the straight track sketch
        # Could also extrude to the body instead of the face, which would be much simpler to implement. That didn't occur to me until after writing this code.
        # extrude_target_face = bent_track_extrude.sideFaces.item(1) # This method does not reliably extract the correct face
        extrude_target_face = None
        straight_track_extrude_faces = straight_track_extrude.sideFaces
        bottom_line_vertex_1 = list(bottom_line.startSketchPoint.geometry.asArray()) # the documentation says asArray returns a list but it appears to actually return a tuple
        bottom_line_vertex_2 = list(bottom_line.endSketchPoint.geometry.asArray())
        # Convert the sketch's coordinates to design's coordinates
        bottom_line_vertex_1[2] = -1*bottom_line_vertex_1[1]
        bottom_line_vertex_1[1] = 0
        bottom_line_vertex_2[2] = -1*bottom_line_vertex_2[1]
        bottom_line_vertex_2[1] = 0
        # futil.log(f'bottom line start vertex: {bottom_line_vertex_1}')
        # futil.log(f'bottom line end vertex: {bottom_line_vertex_2}')
        for straight_track_extrude_face in straight_track_extrude_faces:
            # futil.log(f'face area: {straight_track_extrude_face.area}')
            for edge in straight_track_extrude_face.edges:
                # futil.log(f'edge length: {edge.length}')
                edge_vertex_1 = list(edge.startVertex.geometry.asArray())
                edge_vertex_2 = list(edge.endVertex.geometry.asArray())
                edge_vertex_1[1] = 0.0
                edge_vertex_2[1] = 0.0
                # futil.log(f'edge start vertex: {edge_vertex_1}')
                # futil.log(f'edge end vertex: {edge_vertex_2}')
                if (
                    (are_points_close(edge_vertex_1, bottom_line_vertex_1) and are_points_close(edge_vertex_2, bottom_line_vertex_2))
                    or (are_points_close(edge_vertex_1, bottom_line_vertex_2) and are_points_close(edge_vertex_2, bottom_line_vertex_1))
                ):
                    extrude_target_face = straight_track_extrude_face
            if extrude_target_face:
                break
        # futil.log(f'final face area: {extrude_target_face.area}')
        extrude_input.setOneSideExtent(
            adsk.fusion.ToEntityExtentDefinition.create(extrude_target_face, False),  # False = don't chain faces
            adsk.fusion.ExtentDirections.PositiveExtentDirection
        )
        extrudes.add(extrude_input)

        track_PXPX_body.isVisible = False # hide the body so that it isn't cut by later features


        # Bent track input path sketch
        bent_track_input_path_sketch = sketches.add(yzPlane) # if you want a point to be at (a, b), you must input (-b, -a)
        bent_track_input_path_sketch.name = 'Bent Track Input'
        lines = bent_track_input_path_sketch.sketchCurves.sketchLines
        points = bent_track_input_path_sketch.sketchPoints
        origin_point = bent_track_input_path_sketch.originPoint
        constraints = bent_track_input_path_sketch.geometricConstraints
        dimensions = bent_track_input_path_sketch.sketchDimensions

        start_point = origin_point
        end_point = adsk.core.Point3D.create(-1, -2, 0)
        input_path_line = lines.addByTwoPoints(start_point, end_point)

        # Add dimensions to the input path line
        textPoint = input_path_line.endSketchPoint.geometry.copy()
        textPoint.translateBy(adsk.core.Vector3D.create(0.1,-0.1,0))
        input_path_line_v_dim = dimensions.addDistanceDimension(input_path_line.endSketchPoint, input_path_line.startSketchPoint, adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation, textPoint)
        input_path_line_v_dim.parameter.expression = f'{slope_text} * ( {diameter_text} / 2 + 5 mm )'
        textPoint = input_path_line.geometry.evaluator.getPointAtParameter(0.5)[1].copy()
        textPoint.translateBy(adsk.core.Vector3D.create(-0.25,0,0))
        input_path_line_h_dim = dimensions.addDistanceDimension(input_path_line.endSketchPoint, input_path_line.startSketchPoint, adsk.fusion.DimensionOrientations.VerticalDimensionOrientation, textPoint)
        input_path_line_h_dim.parameter.expression = f'{diameter_text} / 2 + 5 mm'

        # Create and dimension the extrude reference point
        extrude_ref_point = points.add(adsk.core.Point3D.create(1, -1, 0))
        textPoint = input_path_line.startSketchPoint.geometry.copy()
        textPoint.translateBy(adsk.core.Vector3D.create(0.1, -0.3, 0))
        extrude_ref_point_h_dim = dimensions.addDistanceDimension(extrude_ref_point, input_path_line.startSketchPoint, adsk.fusion.DimensionOrientations.VerticalDimensionOrientation, textPoint)
        extrude_ref_point_h_dim.parameter.expression = f'{diameter_text} / 2'
        textPoint = extrude_ref_point.geometry.copy()
        textPoint.translateBy(adsk.core.Vector3D.create(-0.2, 0.2, 0))
        extrude_ref_point_dist_dim = dimensions.addOffsetDimension(input_path_line, extrude_ref_point, textPoint)
        extrude_ref_point_dist_dim.parameter.expression = f'{diameter_text} / 4'

        # Bent track output path sketch
        bent_track_output_path_sketch = sketches.add(xzPlane) # if you want a point to be at (a, b), you must input (a, -b)
        bent_track_output_path_sketch.name = 'Bent Track Output'
        lines = bent_track_output_path_sketch.sketchCurves.sketchLines
        points = bent_track_output_path_sketch.sketchPoints
        origin_point = bent_track_output_path_sketch.originPoint
        constraints = bent_track_output_path_sketch.geometricConstraints
        dimensions = bent_track_output_path_sketch.sketchDimensions

        # Project a sketch point from sourceSketch into targetSketch
        projectedEntities = bent_track_output_path_sketch.project2([extrude_ref_point], True)
        if len(projectedEntities) > 0:
            projected_extr_ref_point = projectedEntities[0]
        
        rec_lines = lines.addTwoPointRectangle(adsk.core.Point3D.create(-1*diameter/2, 0.1, 0), adsk.core.Point3D.create(diameter/2, 0.5, 0))
        # rectangle lines seem to be listed clockwise starting with the top line
        for i in range(rec_lines.count):
            rec_line = rec_lines.item(i)
            if i%2 == 0:
                constraints.addHorizontal(rec_line)
            else:
                constraints.addVertical(rec_line)
            # start_point = rec_line.startSketchPoint.geometry.getData()
            # end_point = rec_line.endSketchPoint.geometry.getData()
            # futil.log(f'rectangle line {i} starts at {start_point} and ends at {end_point}')
        top_rec_line = rec_lines.item(0)
        constraints.addMidPoint(projected_extr_ref_point, top_rec_line)

        # Create output path line
        start_point = origin_point
        end_point = adsk.core.Point3D.create(1, 1, 0)
        output_path_line = lines.addByTwoPoints(start_point, end_point)
        textPoint = output_path_line.startSketchPoint.geometry.copy()
        textPoint.translateBy(adsk.core.Vector3D.create(0.2,-0.1,0))
        output_path_line_h_dim = dimensions.addDistanceDimension(output_path_line.startSketchPoint, output_path_line.endSketchPoint, adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation, textPoint)
        output_path_line_h_dim.parameter.expression = f'{diameter_text} / 2 + 5 mm'
        textPoint = output_path_line.endSketchPoint.geometry.copy()
        textPoint.translateBy(adsk.core.Vector3D.create(0.1,-0.1,0))
        output_path_line_v_dim = dimensions.addDistanceDimension(output_path_line.startSketchPoint, output_path_line.endSketchPoint, adsk.fusion.DimensionOrientations.VerticalDimensionOrientation, textPoint)
        output_path_line_v_dim.parameter.expression = f'{slope_text} * ( {diameter_text} / 2 + 5 mm )'

        # Add the main dimensions
        bottom_rec_line = rec_lines.item(2)
        textPoint = bottom_rec_line.geometry.evaluator.getPointAtParameter(0.5)[1].copy()
        textPoint.translateBy(adsk.core.Vector3D.create(0, 0.1, 0))
        dimension = dimensions.addDistanceDimension(bottom_rec_line.startSketchPoint, bottom_rec_line.endSketchPoint, adsk.fusion.DimensionOrientations.AlignedDimensionOrientation, textPoint)
        dimension.parameter.expression = f'{diameter_text}'
        textPoint = bottom_rec_line.startSketchPoint.geometry.copy()
        textPoint.translateBy(adsk.core.Vector3D.create(0.1,-0.1,0))
        dimension = dimensions.addOffsetDimension(output_path_line, bottom_rec_line.startSketchPoint, textPoint)
        dimension.parameter.expression = f'{diameter_text} / 2 + 2.5 mm'
        
        # Add construction line for trimming later
        start_point = projected_extr_ref_point
        end_point = adsk.core.Point3D.create(1, 1, 0)
        trimming_line = lines.addByTwoPoints(start_point, end_point)
        trimming_line.isConstruction = True
        right_rec_line = rec_lines.item(1)
        constraints.addCoincident(trimming_line.endSketchPoint, right_rec_line)
        textPoint = trimming_line.endSketchPoint.geometry.copy()
        textPoint.translateBy(adsk.core.Vector3D.create(0.1, -0.1, 0))
        dimension = dimensions.addOffsetDimension(output_path_line, trimming_line.endSketchPoint, textPoint)
        dimension.parameter.expression = f'{diameter_text} / 4'

        # Extrude sketch profile
        prof = bent_track_output_path_sketch.profiles.item(0)
        extrude_input = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        extrude_distance = adsk.core.ValueInput.createByString(diameter_text)
        extrude_input.setSymmetricExtent(extrude_distance, True)
        bent_track_extrude = extrudes.add(extrude_input)
        track_PYPX_body = bent_track_extrude.bodies.item(0)
        track_PYPX_body.name = "Track +Y+X"

        # Cut ball paths using pipe features
        path = adsk.fusion.Path.create(input_path_line, adsk.fusion.ChainedCurveOptions.noChainedCurves)
        pipe_input = pipes.createInput(path, adsk.fusion.FeatureOperations.CutFeatureOperation)
        pipe_input.sectionSize = adsk.core.ValueInput.createByReal(diameter)
        pipe = pipes.add(pipe_input)
        pipe.sectionSize.expression = diameter_text
        path = adsk.fusion.Path.create(output_path_line, adsk.fusion.ChainedCurveOptions.noChainedCurves)
        pipe_input = pipes.createInput(path, adsk.fusion.FeatureOperations.CutFeatureOperation)
        pipe_input.sectionSize = adsk.core.ValueInput.createByReal(diameter)
        pipe = pipes.add(pipe_input)
        pipe.sectionSize.expression = diameter_text

        # Cut the track with a sphere
        sphere_sketch = sketches.add(xyPlane)
        sphere_sketch.name = 'Bent Track Sphere'
        arcs = sphere_sketch.sketchCurves.sketchArcs
        lines = sphere_sketch.sketchCurves.sketchLines
        origin_point = sphere_sketch.originPoint
        constraints = sphere_sketch.geometricConstraints
        dimensions = sphere_sketch.sketchDimensions
        
        center = origin_point
        start_point = adsk.core.Point3D.create(0, diameter/2.0, 0)
        end_point = adsk.core.Point3D.create(0, -1*diameter/2.0, 0)
        diameter_line = lines.addByTwoPoints(start_point, end_point)
        arc = arcs.addByCenterStartEnd(center, diameter_line.startSketchPoint, diameter_line.endSketchPoint)

        textPoint = arc.centerSketchPoint.geometry.copy()
        textPoint.translateBy(adsk.core.Vector3D.create(0.2,0.2,0))
        dimension = dimensions.addDiameterDimension(arc, textPoint, True)
        dimension.parameter.expression = diameter_text

        circle_center = arc.centerSketchPoint
        constraints.addCoincident(circle_center, origin_point)
        constraints.addCoincident(circle_center, diameter_line)
        constraints.addVertical(diameter_line)

        prof = sphere_sketch.profiles.item(0)
        revInput = revolves.createInput(prof, diameter_line, adsk.fusion.FeatureOperations.CutFeatureOperation)
        revInput.setAngleExtent(False, adsk.core.ValueInput.createByReal(math.pi * 2))
        revolve = revolves.add(revInput)


        # Bent track trim sketch
        bent_track_trim_sketch = sketches.add(xzPlane) # if you want a point to be at (a, b), you must input (a, -b)
        bent_track_trim_sketch.name = 'Bent Track Trim'
        lines = bent_track_trim_sketch.sketchCurves.sketchLines
        points = bent_track_trim_sketch.sketchPoints
        origin_point = bent_track_trim_sketch.originPoint
        constraints = bent_track_trim_sketch.geometricConstraints
        dimensions = bent_track_trim_sketch.sketchDimensions

        projectedEntities = bent_track_trim_sketch.project2([trimming_line], True)
        projected_trimming_line = projectedEntities[0]
        
        intermediate_point = adsk.core.Point3D.create(projected_trimming_line.endSketchPoint.geometry.x, projected_trimming_line.startSketchPoint.geometry.y, 0)
        # points.add(intermediate_point)
        # Must add coincident constraints or else the the horizontal and vertical lines won't stay attached to the projected line if it moves
        # I also have to use a Point3D copy of the projected line endpoints
        h_line = lines.addByTwoPoints(projected_trimming_line.startSketchPoint.geometry.copy(), intermediate_point)
        v_line = lines.addByTwoPoints(h_line.endSketchPoint, projected_trimming_line.endSketchPoint.geometry.copy())
        constraints.addHorizontal(h_line)
        constraints.addVertical(v_line)
        constraints.addCoincident(h_line.startSketchPoint, projected_trimming_line.startSketchPoint)
        constraints.addCoincident(v_line.endSketchPoint, projected_trimming_line.endSketchPoint)

        # Trim the bent track
        prof = bent_track_trim_sketch.profiles.item(0)
        extrude_distance = adsk.core.ValueInput.createByString(diameter_text)
        extrude = extrudes.addSimple(prof, extrude_distance, adsk.fusion.FeatureOperations.CutFeatureOperation)

        # Make the track tall so that it easily combines into a 3D printable solid later
        prof = track_footprint_sketch.profiles.item(0)
        extrude_input = extrudes.createInput(prof, adsk.fusion.FeatureOperations.JoinFeatureOperation)
        # extrude_distance_value_input = adsk.core.ValueInput.createByString(diameter_text)
        # extrude_distance_extent = adsk.fusion.DistanceExtentDefinition.create(extrude_distance_value_input)
        # straight_track_extrude = extrudes.add(extrude_input)
        extrude_offset_text = f'-1 * ({num_x_cells_text} * {num_y_cells_text} * {diameter_text} * {slope_text} + {diameter_text} / 2 + 10 mm)'
        start_offset = adsk.core.ValueInput.createByString(extrude_offset_text)
        extrude_input.startExtent = adsk.fusion.OffsetStartDefinition.create(start_offset)
        extent_definition = adsk.fusion.ToEntityExtentDefinition.create(track_PYPX_body, True)
        extrude_input.setOneSideExtent(
            extent_definition,
            adsk.fusion.ExtentDirections.PositiveExtentDirection
        )
        extrudes.add(extrude_input)

        track_PYPX_body.isVisible = False

        # Create the base tracks
        track_PYPY = copy_pastes.add(track_PXPX_body)
        track_PYPY_body = track_PYPY.bodies.item(0)
        object_collection = adsk.core.ObjectCollection.create()
        object_collection.add(track_PYPY_body)
        move_input = moves.createInput2(object_collection)
        move_input.defineAsRotate(zAxis, adsk.core.ValueInput.createByString('90 deg'))
        moves.add(move_input)
        track_PYPY_body.name = 'Track +Y+Y'
        track_PYPY_body.isVisible = False
        track_NXNX = copy_pastes.add(track_PXPX_body)
        track_NXNX_body = track_NXNX.bodies.item(0)
        object_collection = adsk.core.ObjectCollection.create()
        object_collection.add(track_NXNX_body)
        move_input = moves.createInput2(object_collection)
        move_input.defineAsRotate(zAxis, adsk.core.ValueInput.createByString('180 deg'))
        moves.add(move_input)
        track_NXNX_body.name = 'Track -X-X'
        track_NXNX_body.isVisible = False
        track_NYNY = copy_pastes.add(track_PXPX_body)
        track_NYNY_body = track_NYNY.bodies.item(0)
        object_collection = adsk.core.ObjectCollection.create()
        object_collection.add(track_NYNY_body)
        move_input = moves.createInput2(object_collection)
        move_input.defineAsRotate(zAxis, adsk.core.ValueInput.createByString('270 deg'))
        moves.add(move_input)
        track_NYNY_body.name = 'Track -Y-Y'
        track_NYNY_body.isVisible = False

        track_NXPY = copy_pastes.add(track_PYPX_body)
        track_NXPY_body = track_NXPY.bodies.item(0)
        object_collection = adsk.core.ObjectCollection.create()
        object_collection.add(track_NXPY_body)
        move_input = moves.createInput2(object_collection)
        move_input.defineAsRotate(zAxis, adsk.core.ValueInput.createByString('90 deg'))
        moves.add(move_input)
        track_NXPY_body.name = 'Track -X+Y'
        track_NXPY_body.isVisible = False
        track_NYNX = copy_pastes.add(track_PYPX_body)
        track_NYNX_body = track_NYNX.bodies.item(0)
        object_collection = adsk.core.ObjectCollection.create()
        object_collection.add(track_NYNX_body)
        move_input = moves.createInput2(object_collection)
        move_input.defineAsRotate(zAxis, adsk.core.ValueInput.createByString('180 deg'))
        moves.add(move_input)
        track_NYNX_body.name = 'Track -Y-X'
        track_NYNX_body.isVisible = False
        track_PXNY = copy_pastes.add(track_PYPX_body)
        track_PXNY_body = track_PXNY.bodies.item(0)
        object_collection = adsk.core.ObjectCollection.create()
        object_collection.add(track_PXNY_body)
        move_input = moves.createInput2(object_collection)
        move_input.defineAsRotate(zAxis, adsk.core.ValueInput.createByString('270 deg'))
        moves.add(move_input)
        track_PXNY_body.name = 'Track +X-Y'
        track_PXNY_body.isVisible = False

        object_collection = adsk.core.ObjectCollection.create()
        object_collection.add(track_PYPX_body)
        mirrorInput = mirrors.createInput(object_collection, yzPlane)
        track_PYNX = mirrors.add(mirrorInput)
        track_PYNX_body = track_PYNX.bodies.item(0)
        track_PYNX_body.name = 'Track +Y-X'
        track_PYNX_body.isVisible = False

        track_NXNY = copy_pastes.add(track_PYNX_body)
        track_NXNY_body = track_NXNY.bodies.item(0)
        object_collection = adsk.core.ObjectCollection.create()
        object_collection.add(track_NXNY_body)
        move_input = moves.createInput2(object_collection)
        move_input.defineAsRotate(zAxis, adsk.core.ValueInput.createByString('90 deg'))
        moves.add(move_input)
        track_NXNY_body.name = 'Track -X-Y'
        track_NXNY_body.isVisible = False
        track_NYPX = copy_pastes.add(track_PYNX_body)
        track_NYPX_body = track_NYPX.bodies.item(0)
        object_collection = adsk.core.ObjectCollection.create()
        object_collection.add(track_NYPX_body)
        move_input = moves.createInput2(object_collection)
        move_input.defineAsRotate(zAxis, adsk.core.ValueInput.createByString('180 deg'))
        moves.add(move_input)
        track_NYPX_body.name = 'Track -Y+X'
        track_NYPX_body.isVisible = False
        track_PXPY = copy_pastes.add(track_PYNX_body)
        track_PXPY_body = track_PXPY.bodies.item(0)
        object_collection = adsk.core.ObjectCollection.create()
        object_collection.add(track_PXPY_body)
        move_input = moves.createInput2(object_collection)
        move_input.defineAsRotate(zAxis, adsk.core.ValueInput.createByString('270 deg'))
        moves.add(move_input)
        track_PXPY_body.name = 'Track +X+Y'
        track_PXPY_body.isVisible = False

        # Create a matrix that represents the track path
        matrix = path_generator.generate_path(num_x_cells, num_y_cells)
        futil.log(f'matrix: {matrix}')
        # Create a matrix showing what type of track should be used
        type_matrix = path_generator.generate_type_matrix()
        base_track_bodies = [
            track_PXPX_body, track_PYPY_body, track_NXNX_body, track_NYNY_body, 
            track_PYPX_body, track_NXPY_body, track_NYNX_body, track_PXNY_body,
            track_PYNX_body, track_NXNY_body, track_NYPX_body, track_PXPY_body
        ]

        # Copy and move the base tracks to the positions specified in the matrix
        x_pos = 0.0
        y_pos = 0.0
        z_pos = 0.0
        z_drop = diameter*slope # float that represents how much the height drops after each cell
        copied_track_bodies = []
        for row in range(len(matrix)):
            y_pos = -1 * row * diameter
            for col in range(len(matrix[0])):
                x_pos = col * diameter
                cell_val = matrix[row][col]
                cell_type = type_matrix[row][col]
                z_pos = -1 * (cell_val-1) * z_drop
                cell_body = base_track_bodies[cell_type]
                track_copy = copy_pastes.add(cell_body)
                track_copy_body = track_copy.bodies.item(0)

                object_collection = adsk.core.ObjectCollection.create()
                object_collection.add(track_copy_body)
                move_input = moves.createInput2(object_collection)
                x_delta = adsk.core.ValueInput.createByReal(x_pos)
                y_delta = adsk.core.ValueInput.createByReal(y_pos)
                z_delta = adsk.core.ValueInput.createByReal(z_pos)
                move_input.defineAsTranslateXYZ(x_delta, y_delta, z_delta, True)
                moves.add(move_input)

                copied_track_bodies.append(track_copy_body)
                

        # Combine all the track segments together
        target_body = copied_track_bodies[0]
        tool_bodies = adsk.core.ObjectCollection.create()
        for i in range(1, len(copied_track_bodies)):
            tool_body = copied_track_bodies[i]
            tool_bodies.add(tool_body)
        combine_feature_input = combines.createInput(target_body, tool_bodies)
        combine_feature_input.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
        combine_feature_input.isKeepToolBodies = False
        combines.add(combine_feature_input)

        # Trim the track so that it has a flat base
        track_base_trimmer_sketch = sketches.add(xyPlane)
        track_base_trimmer_sketch.name = 'Track Base Trimmer'
        lines = track_base_trimmer_sketch.sketchCurves.sketchLines
        points = track_base_trimmer_sketch.sketchPoints
        origin_point = track_base_trimmer_sketch.originPoint
        constraints = track_base_trimmer_sketch.geometricConstraints
        dimensions = track_base_trimmer_sketch.sketchDimensions

        rectangle_point_1 = adsk.core.Point3D.create(-1*diameter/2, diameter/2, 0)
        rectangle_point_2 = adsk.core.Point3D.create(num_x_cells*diameter-1*diameter/2, -1*num_y_cells*diameter+diameter/2, 0)
        rec_lines = lines.addTwoPointRectangle(rectangle_point_1, rectangle_point_2)
        for i in range(rec_lines.count):
            rec_line = rec_lines.item(i)
            if i%2 == 0:
                constraints.addHorizontal(rec_line)
            else:
                constraints.addVertical(rec_line)
        top_rec_line = rec_lines.item(0)
        left_rec_line = rec_lines.item(3)
        textPoint = top_rec_line.geometry.evaluator.getPointAtParameter(0.5)[1].copy()
        textPoint.translateBy(adsk.core.Vector3D.create(0, 0.1, 0))
        dimension = dimensions.addDistanceDimension(top_rec_line.startSketchPoint, top_rec_line.endSketchPoint, adsk.fusion.DimensionOrientations.AlignedDimensionOrientation, textPoint)
        dimension.parameter.expression = f'{num_x_cells} * {diameter_text}'
        textPoint = left_rec_line.geometry.evaluator.getPointAtParameter(0.5)[1].copy()
        textPoint.translateBy(adsk.core.Vector3D.create(-0.1, 0, 0))
        dimension = dimensions.addDistanceDimension(left_rec_line.startSketchPoint, left_rec_line.endSketchPoint, adsk.fusion.DimensionOrientations.AlignedDimensionOrientation, textPoint)
        dimension.parameter.expression = f'{num_y_cells} * {diameter_text}'
        textPoint = top_rec_line.startSketchPoint.geometry.copy()
        textPoint.translateBy(adsk.core.Vector3D.create(0.2, 0.2, 0))
        dimension = dimensions.addDistanceDimension(top_rec_line.startSketchPoint, origin_point, adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation, textPoint)
        dimension.parameter.expression = f'{diameter_text} / 2'
        textPoint = top_rec_line.startSketchPoint.geometry.copy()
        textPoint.translateBy(adsk.core.Vector3D.create(-0.2, -0.2, 0))
        dimension = dimensions.addDistanceDimension(top_rec_line.startSketchPoint, origin_point, adsk.fusion.DimensionOrientations.VerticalDimensionOrientation, textPoint)
        dimension.parameter.expression = f'{diameter_text} / 2'

        prof = track_base_trimmer_sketch.profiles.item(0)
        extrude_input = extrudes.createInput(prof, adsk.fusion.FeatureOperations.CutFeatureOperation)
        # extrude_distance_value_input = adsk.core.ValueInput.createByString(diameter_text)
        # extrude_distance_extent = adsk.fusion.DistanceExtentDefinition.create(extrude_distance_value_input)
        # straight_track_extrude = extrudes.add(extrude_input)
        extrude_offset_text = f'-1 * ({num_x_cells_text} * {num_y_cells_text} * {diameter_text} * {slope_text} + {diameter_text} / 2 + 10 mm)'
        start_offset = adsk.core.ValueInput.createByString(extrude_offset_text)
        extrude_input.startExtent = adsk.fusion.OffsetStartDefinition.create(start_offset)
        extrude_distance = adsk.core.ValueInput.createByString(f'-1 * ({num_x_cells_text} * {num_y_cells_text} * {diameter_text} * {slope_text} + {diameter_text} / 2 + 10 mm)')
        extrude_input.setOneSideExtent(
            adsk.fusion.DistanceExtentDefinition.create(extrude_distance),  # False = don't chain faces
            adsk.fusion.ExtentDirections.PositiveExtentDirection
        )
        extrudes.add(extrude_input)


        # extent_distance_2 = adsk.fusion.DistanceExtentDefinition.create(mm10)
        # # Create a start extent that starts from a brep face with an offset of 10 mm.
        # start_from = adsk.fusion.FromEntityStartDefinition.create(body1.faces.item(0), mm10)
        # # taperAngle should be 0 because extrude start face is not a planar face in this case
        # extrudeInput.setOneSideExtent(extent_distance_2, adsk.fusion.ExtentDirections.PositiveExtentDirection)        
        # extrudeInput.startExtent = start_from
        # # Create the extrusion
        # extrude3 = extrudes.add(extrudeInput)



        # #  Create all pipes
        # isFirstPipe = True
        # firstPipe = None
        # for entity in stored_curve_entities:
        #     path = adsk.fusion.Path.create(entity, adsk.fusion.ChainedCurveOptions.noChainedCurves)
        #     sectionSize = diameter_text
        #     pipe = create_pipe(comp, path, sectionSize)
        #     if isFirstPipe:
        #         firstPipe = pipe
        #         isFirstPipe = False
        # firstTimelineFeature = firstPipe

        # # Create a sphere
        # sketches = comp.sketches
        # xyPlane = comp.xYConstructionPlane
        # sketch = sketches.add(xyPlane)
        # if not firstTimelineFeature:
        #     firstTimelineFeature = sketch
        # arcs = sketch.sketchCurves.sketchArcs
        # lines = sketch.sketchCurves.sketchLines
        
        # center = adsk.core.Point3D.create(0, 0, 0)
        # startPoint = adsk.core.Point3D.create(0, diameter/2.0, 0)
        # endPoint = adsk.core.Point3D.create(0, -1*diameter/2.0, 0)
        # diameterLine = lines.addByTwoPoints(startPoint, endPoint)
        # arc = arcs.addByCenterStartEnd(center, diameterLine.startSketchPoint, diameterLine.endSketchPoint) # using the line's endpoint attributes joins the line to the arc

        # textPoint: adsk.core.Point3D = arc.centerSketchPoint.geometry.copy()
        # textPoint.translateBy(adsk.core.Vector3D.create(0.25,0.25,0))
        # dimensions: adsk.fusion.SketchDimensions = sketch.sketchDimensions
        # diameterDim: adsk.fusion.SketchDiameterDimension = dimensions.addDiameterDimension(arc, textPoint, True)
        # modelPrm: adsk.fusion.ModelParameter = diameterDim.parameter
        # # modelPrm.expression = diam_param.name
        # modelPrm.expression = diameter_text

        # origin_point = sketch.originPoint
        # circle_center = arc.centerSketchPoint
        # constraints = sketch.geometricConstraints
        # circle_coincident_constraint = constraints.addCoincident(circle_center, origin_point)
        # line_coincident_constraint = constraints.addCoincident(circle_center, diameterLine)
        # vertical_constraint = constraints.addVertical(diameterLine)

        # prof = sketch.profiles.item(0)
        # revolves = comp.features.revolveFeatures
        # revInput = revolves.createInput(prof, diameterLine, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        # revInput.setAngleExtent(False, adsk.core.ValueInput.createByReal(math.pi * 2))
        # sphere = revolves.add(revInput)

        # fromPoint = des.rootComponent.originConstructionPoint

        # #  Create all spheres
        # for entity in stored_point_entities:
        #     toPoint = entity
        #     create_sphere(comp, sphere, fromPoint, toPoint)

        # # Parametrically remove the reference sphere at the origin
        # removeFeatures = features.removeFeatures
        # removeSphere = removeFeatures.add(sphere.bodies[0]) # sphere.bodies.item(0) also seems to work

        # # Put the timeline features into a group
        # timelineGroups = des.timeline.timelineGroups
        # timelineStartIndex = firstTimelineFeature.timelineObject.index
        # timelineEndIndex = removeSphere.timelineObject.index
        # timelineGroup = timelineGroups.add(timelineStartIndex, timelineEndIndex)
        # timelineGroup.name = 'Ball Track Cutter'

        
        # Save the current values as attributes.
        settings = {'Diameter': str(self.diameterValueInput.value)}
        # settings = {'Diameter': str(self.diameterValueInput.value),
        #             'IgnoreArcCenters': self.ignoreArcCentersValueInput.value}

        jsonSettings = json.dumps(settings)

        attribs = des.attributes
        attribs.add('MarbleRun', 'settings', jsonSettings)


def are_points_close(p1, p2, tol=1e-6):
    return math.dist(p1, p2) < tol


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

