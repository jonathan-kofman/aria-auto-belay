import adsk.core, adsk.fusion, adsk.cam

def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    design = app.activeProduct
    
    # Analyze the STEP file
    step_path = 'outputs/cad/step/llm_mechanical_clock_escapement_wheel_tooth.step'
    geometry_data = TOOL_CALL:analyze_step(step_path)
    
    if not geometry_data or 'error' in geometry_data:
        ui.messageBox('Error analyzing STEP file. Please check the file path and try again.')
        return
    
    # Select tools based on geometry data
    holes_csv = ','.join(map(str, geometry_data['holes']))
    tool_recommendations = TOOL_CALL:select_tools(float(geometry_data['min_feature_size']), float(geometry_data['max_dim_mm']), holes_csv)
    
    if not tool_recommendations or 'error' in tool_recommendations:
        ui.messageBox('Error selecting tools. Please check the input values and try again.')
        return
    
    # Create CAM setup
    design_root_comp = design.rootComponent
    fixed_box_stock = adsk.cam.FixedBoxStock.create(design_root_comp, adsk.core.Point3D.create(0, 0, 0), adsk.core.Vector3D.create(21.5, 21.5, 4.0), 1.0, 1.5)
    
    # Create CAM operations
    cam_features = design_root_comp.features.camFeatures
    
    # 3D Adaptive Clearing (Roughing) with EM-3 endmill
    em3_endmill = adsk.cam.EndMillTool.create(tool_recommendations['EM-3']['diameter'], tool_recommendations['EM-3']['flutes'])
    roughing_op = cam_features.addAdaptiveClearanceOperation(fixed_box_stock, em3_endmill)
    roughing_op.operationType = adsk.cam.AdaptiveOperationTypes.ThreeDAdaptiveClearanceType
    roughing_op.rapidFeedRate = 1000.0
    roughing_op.toolPathType = adsk.cam.ToolPathTypes.ParallelToolPathType
    roughing_op.useStockBoundary = True
    roughing_op.stockBoundaryOffset = -1.5
    
    # Parallel Finishing Pass with EM-3 endmill
    finishing_op = cam_features.addAdaptiveClearanceOperation(fixed_box_stock, em3_endmill)
    finishing_op.operationType = adsk.cam.AdaptiveOperationTypes.ThreeDAdaptiveClearanceType
    finishing_op.rapidFeedRate = 1000.0
    finishing_op.toolPathType = adsk.cam.ToolPathTypes.ParallelToolPathType
    finishing_op.useStockBoundary = True
    finishing_op.stockBoundaryOffset = -0.5
    
    # Contour Operation for Walls with BN-6 ball nose
    bn6_ball_nose = adsk.cam.BallNoseEndMillTool.create(tool_recommendations['BN-6']['diameter'], tool_recommendations['BN-6']['flutes'])
    contour_op = cam_features.addContourOperation(fixed_box_stock, bn6_ball_nose)
    contour_op.operationType = adsk.cam.ContourOperationTypes.ParallelContourType
    contour_op.rapidFeedRate = 1000.0
    
    # Drill Cycles for Detected Holes with DR-3 drill
    dr3_drill = adsk.cam.StandardDrillTool.create(tool_recommendations['DR-3']['diameter'])
    for hole in geometry_data['holes']:
        drill_op = cam_features.addStandardDrillOperation(fixed_box_stock, dr3_drill)
        drill_op.operationType = adsk.cam.StandardDrillOperationTypes.SinglePointPeckedDrilling
        drill_op.holeDiameter = hole
        drill_op.depth = 1.5
        drill_op.plungeFeedRate = 727.0
    
    # Validate CAM script
    script_json = {
        'operations': [
            {'type': 'AdaptiveClearance', 'tool': 'EM-3', 'feed': 1940, 'speed': 9702},
            {'type': 'AdaptiveClearance', 'tool': 'EM-3', 'feed': 1940, 'speed': 9702},
            {'type': 'Contour', 'tool': 'BN-6', 'feed': 970, 'speed': 4851},
            {'type': 'StandardDrill', 'tool': 'DR-3', 'feed': 2910, 'speed': 9702}
        ]
    }
    TOOL_CALL:validate_cam(script_json)
    
    # Post G-code
    post_processor = adsk.cam.PostProcessors.getPostProcessor('Fanuc')
    output_folder = 'C:\\Users\\jonko\\Downloads\\aria-auto-belay\\outputs\\cam\\llm_mechanical_clock_escapement_wheel_tooth\\gcode'
    post_processor.post(fixed_box_stock, output_folder)
    
    ui.messageBox('CAM operations created and G-code posted successfully.')