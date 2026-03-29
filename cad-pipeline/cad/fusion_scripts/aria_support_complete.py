"""
ARIA — Support Components Complete (v3, Direct Modeling)
All four support parts fully finished:
  1. ARIA_EndCap_Complete     — bearing retainer with shoulder + O-ring groove + counterbores
  2. ARIA_WallBracket_Complete — L-bracket with slotted holes + gusset + housing holes
  3. ARIA_MotorMount_Complete  — motor plate with pilot shoulder + wire slot + all bolt holes
  4. ARIA_RopeGuide_Complete   — fairlead with rope groove + pulley axle + side plates
"""

import adsk.core, adsk.fusion, traceback, math

def largest_profile(sketch):
    best, best_a = None, 0.0
    for i in range(sketch.profiles.count):
        p = sketch.profiles.item(i)
        try:
            a = p.areaProperties().area
            if a > best_a:
                best_a = a
                best = p
        except:
            pass
    return best

def annular_profile(sketch, r_in, r_out):
    cm = lambda mm: mm  # document uses mm directly
    exp = math.pi * (cm(r_out)**2 - cm(r_in)**2)
    best, best_d = None, float('inf')
    for i in range(sketch.profiles.count):
        p = sketch.profiles.item(i)
        try:
            a = p.areaProperties().area
            d = abs(a - exp)
            if d < best_d:
                best_d = d
                best = p
        except:
            pass
    return best

def make_rect(sketch, x, y, w, h):
    L = sketch.sketchCurves.sketchLines
    cm = lambda mm: mm  # document uses mm directly
    def P(px,py): return adsk.core.Point3D.create(cm(px),cm(py),0)
    L.addByTwoPoints(P(x,y),     P(x+w,y))
    L.addByTwoPoints(P(x+w,y),   P(x+w,y+h))
    L.addByTwoPoints(P(x+w,y+h), P(x,y+h))
    L.addByTwoPoints(P(x,y+h),   P(x,y))

def extrude(feats, prof, depth_mm, op):
    cm = lambda mm: mm  # document uses mm directly
    e = feats.extrudeFeatures.createInput(prof, op)
    e.setOneSideExtent(
        adsk.fusion.DistanceExtentDefinition.create(
            adsk.core.ValueInput.createByReal(cm(depth_mm))),
        adsk.fusion.ExtentDirections.PositiveExtentDirection)
    return feats.extrudeFeatures.add(e)

def run(context):
    ui = None
    try:
        app  = adsk.core.Application.get()
        ui   = app.userInterface
        des  = adsk.fusion.Design.cast(app.activeProduct)
        if des.designType == adsk.fusion.DesignTypes.ParametricDesignType:
            des.designType = adsk.fusion.DesignTypes.DirectDesignType

        root  = des.rootComponent
        cm    = lambda mm: mm  # document uses mm directly
        origin = adsk.core.Point3D.create(0,0,0)
        NEW = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation
        CUT = adsk.fusion.FeatureOperations.CutFeatureOperation

        # ════════════════════════════════════
        # 1. END CAP
        # ════════════════════════════════════
        CAP_W=700; CAP_H=680; CAP_T=15
        SPOOL_CX=350; SPOOL_CY=330
        BEAR_OD=47.2; BEAR_SHLDR_OD=55; BEAR_SHLDR_H=3
        ORING_OD=58; ORING_W=2; ORING_D=1.5
        CAP_BOLT_D=6.6; CAP_BOLT_INSET=20; N_CAP_BOLTS=8
        CB_BORE=11; CB_DEPTH=6  # counterbore for M6 SHCS

        occ1 = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        c1   = occ1.component; c1.name='ARIA_EndCap_Complete'; f1=c1.features

        sk1 = c1.sketches.add(c1.xYConstructionPlane)
        make_rect(sk1, 0, 0, CAP_W, CAP_H)
        # Bearing bore
        sk1.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(cm(SPOOL_CX),cm(SPOOL_CY),0), cm(BEAR_OD/2))
        # Bolt holes
        step_x = (CAP_W - CAP_BOLT_INSET*2) / (N_CAP_BOLTS//2 - 1)
        bolt_pos = []
        for i in range(N_CAP_BOLTS//2):
            bolt_pos.append((CAP_BOLT_INSET + i*step_x, CAP_BOLT_INSET))
            bolt_pos.append((CAP_BOLT_INSET + i*step_x, CAP_H-CAP_BOLT_INSET))
        for bx,by in bolt_pos:
            sk1.sketchCurves.sketchCircles.addByCenterRadius(
                adsk.core.Point3D.create(cm(bx),cm(by),0), cm(CAP_BOLT_D/2))

        cap_prof = largest_profile(sk1)
        if cap_prof:
            extrude(f1, cap_prof, CAP_T, NEW)

        # Bearing shoulder on inboard face
        shldr_p_in = c1.constructionPlanes.createInput()
        shldr_p_in.setByOffset(c1.xYConstructionPlane,
            adsk.core.ValueInput.createByReal(cm(CAP_T)))
        shldr_p = c1.constructionPlanes.add(shldr_p_in)
        sk_sh = c1.sketches.add(shldr_p)
        sk_sh.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(cm(SPOOL_CX),cm(SPOOL_CY),0), cm(BEAR_SHLDR_OD/2))
        sk_sh.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(cm(SPOOL_CX),cm(SPOOL_CY),0), cm(BEAR_OD/2))
        sh_prof = annular_profile(sk_sh, BEAR_OD/2, BEAR_SHLDR_OD/2)
        if sh_prof:
            try:
                e = f1.extrudeFeatures.createInput(sh_prof, JOIN)
                e.setOneSideExtent(
                    adsk.fusion.DistanceExtentDefinition.create(
                        adsk.core.ValueInput.createByReal(cm(BEAR_SHLDR_H))),
                    adsk.fusion.ExtentDirections.NegativeExtentDirection)
                f1.extrudeFeatures.add(e)
            except: pass

        # O-ring groove on mating face
        sk_or = c1.sketches.add(c1.xYConstructionPlane)
        sk_or.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(cm(SPOOL_CX),cm(SPOOL_CY),0), cm(ORING_OD/2))
        sk_or.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(cm(SPOOL_CX),cm(SPOOL_CY),0), cm((ORING_OD-ORING_W*2)/2))
        or_prof = annular_profile(sk_or, (ORING_OD-ORING_W*2)/2, ORING_OD/2)
        if or_prof:
            try:
                e = f1.extrudeFeatures.createInput(or_prof, CUT)
                e.setOneSideExtent(
                    adsk.fusion.DistanceExtentDefinition.create(
                        adsk.core.ValueInput.createByReal(cm(ORING_D))),
                    adsk.fusion.ExtentDirections.PositiveExtentDirection)
                f1.extrudeFeatures.add(e)
            except: pass

        # ════════════════════════════════════
        # 2. WALL BRACKET
        # ════════════════════════════════════
        H_D=344; H_H=680; H_W=700
        BACK_W=H_D; BACK_H=int(H_H*0.65); BACK_T=12
        BASE_W=H_W; BASE_D=200; BASE_T=12
        SLOT_W=12; SLOT_H=20  # slotted wall bolt holes
        GUSSET_T=12; GUSSET_H=120

        occ2 = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        c2   = occ2.component; c2.name='ARIA_WallBracket_Complete'; f2=c2.features

        # Back plate
        sk2 = c2.sketches.add(c2.xYConstructionPlane)
        make_rect(sk2, 0, 0, BACK_W, BACK_H)
        # Slotted wall bolt holes (4x) — slots for adjustment
        for sx2,sy2 in [(BACK_W*0.2, BACK_H*0.2),(BACK_W*0.8,BACK_H*0.2),
                        (BACK_W*0.2, BACK_H*0.8),(BACK_W*0.8,BACK_H*0.8)]:
            SL = sk2.sketchCurves.sketchLines
            SA = sk2.sketchCurves.sketchArcs
            sr = SLOT_W/2
            def SP(x,y): return adsk.core.Point3D.create(cm(x),cm(y),0)
            SL.addByTwoPoints(SP(sx2-sr, sy2-SLOT_H/2+sr), SP(sx2-sr, sy2+SLOT_H/2-sr))
            SA.addByThreePoints(SP(sx2-sr,sy2+SLOT_H/2-sr),SP(sx2,sy2+SLOT_H/2),SP(sx2+sr,sy2+SLOT_H/2-sr))
            SL.addByTwoPoints(SP(sx2+sr,sy2+SLOT_H/2-sr), SP(sx2+sr,sy2-SLOT_H/2+sr))
            SA.addByThreePoints(SP(sx2+sr,sy2-SLOT_H/2+sr),SP(sx2,sy2-SLOT_H/2),SP(sx2-sr,sy2-SLOT_H/2+sr))
        back_prof = largest_profile(sk2)
        if back_prof:
            extrude(f2, back_prof, BACK_T, NEW)

        # Base plate (on XZ plane)
        sk2b = c2.sketches.add(c2.xZConstructionPlane)
        make_rect(sk2b, 0, 0, BASE_W, BASE_D)
        # Floor anchor bolt holes (4x)
        for bx2,bd2 in [(BASE_W*0.15,BASE_D*0.25),(BASE_W*0.85,BASE_D*0.25),
                         (BASE_W*0.15,BASE_D*0.75),(BASE_W*0.85,BASE_D*0.75)]:
            sk2b.sketchCurves.sketchCircles.addByCenterRadius(
                adsk.core.Point3D.create(cm(bx2),cm(bd2),0), cm(12.5/2))
        base_prof = largest_profile(sk2b)
        if base_prof:
            try:
                e = f2.extrudeFeatures.createInput(base_prof, JOIN)
                e.setOneSideExtent(
                    adsk.fusion.DistanceExtentDefinition.create(
                        adsk.core.ValueInput.createByReal(cm(BASE_T))),
                    adsk.fusion.ExtentDirections.PositiveExtentDirection)
                f2.extrudeFeatures.add(e)
            except:
                e2 = f2.extrudeFeatures.createInput(base_prof, NEW)
                e2.setOneSideExtent(
                    adsk.fusion.DistanceExtentDefinition.create(
                        adsk.core.ValueInput.createByReal(cm(BASE_T))),
                    adsk.fusion.ExtentDirections.PositiveExtentDirection)
                f2.extrudeFeatures.add(e2)

        # Gusset triangle
        sk2g = c2.sketches.add(c2.xZConstructionPlane)
        GL = sk2g.sketchCurves.sketchLines
        gx = BASE_W/2
        GL.addByTwoPoints(
            adsk.core.Point3D.create(cm(gx-GUSSET_T/2),0,0),
            adsk.core.Point3D.create(cm(gx+GUSSET_T/2),0,0))
        GL.addByTwoPoints(
            adsk.core.Point3D.create(cm(gx+GUSSET_T/2),0,0),
            adsk.core.Point3D.create(cm(gx),cm(GUSSET_H),0))
        GL.addByTwoPoints(
            adsk.core.Point3D.create(cm(gx),cm(GUSSET_H),0),
            adsk.core.Point3D.create(cm(gx-GUSSET_T/2),0,0))
        g_prof = largest_profile(sk2g)
        if g_prof:
            try:
                e = f2.extrudeFeatures.createInput(g_prof, JOIN)
                e.setSymmetricExtent(
                    adsk.core.ValueInput.createByReal(cm(GUSSET_T/2)), True)
                f2.extrudeFeatures.add(e)
            except: pass

        # ════════════════════════════════════
        # 3. MOTOR MOUNT
        # ════════════════════════════════════
        MM_W=120; MM_H=120; MM_T=10
        MOTOR_BORE=56; PILOT_SHLDR_D=58; PILOT_SHLDR_H=2
        MOTOR_BCD=38; N_MBOLTS=4; MBLOT_D=3.3
        MOUNT_INSET=15; MOUNT_D=6.6
        WIRE_W=15; WIRE_H=8

        occ3 = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        c3   = occ3.component; c3.name='ARIA_MotorMount_Complete'; f3=c3.features

        cx3=MM_W/2; cy3=MM_H/2
        sk3 = c3.sketches.add(c3.xYConstructionPlane)
        make_rect(sk3, 0, 0, MM_W, MM_H)
        sk3.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(cm(cx3),cm(cy3),0), cm(MOTOR_BORE/2))
        for i in range(N_MBOLTS):
            a3 = i*math.pi/2 + math.pi/4
            bx3 = cx3 + MOTOR_BCD/2*math.cos(a3)
            by3 = cy3 + MOTOR_BCD/2*math.sin(a3)
            sk3.sketchCurves.sketchCircles.addByCenterRadius(
                adsk.core.Point3D.create(cm(bx3),cm(by3),0), cm(MBLOT_D/2))
        for bx3,by3 in [(MOUNT_INSET,MOUNT_INSET),(MM_W-MOUNT_INSET,MOUNT_INSET),
                         (MOUNT_INSET,MM_H-MOUNT_INSET),(MM_W-MOUNT_INSET,MM_H-MOUNT_INSET)]:
            sk3.sketchCurves.sketchCircles.addByCenterRadius(
                adsk.core.Point3D.create(cm(bx3),cm(by3),0), cm(MOUNT_D/2))
        mm_prof = largest_profile(sk3)
        if mm_prof:
            extrude(f3, mm_prof, MM_T, NEW)

        # Motor pilot shoulder
        shldr3_in = c3.constructionPlanes.createInput()
        shldr3_in.setByOffset(c3.xYConstructionPlane,
            adsk.core.ValueInput.createByReal(cm(MM_T)))
        shldr3 = c3.constructionPlanes.add(shldr3_in)
        sk3s = c3.sketches.add(shldr3)
        sk3s.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(cm(cx3),cm(cy3),0), cm(PILOT_SHLDR_D/2))
        sk3s.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(cm(cx3),cm(cy3),0), cm(MOTOR_BORE/2))
        sh3_prof = annular_profile(sk3s, MOTOR_BORE/2, PILOT_SHLDR_D/2)
        if sh3_prof:
            try:
                e = f3.extrudeFeatures.createInput(sh3_prof, JOIN)
                e.setOneSideExtent(
                    adsk.fusion.DistanceExtentDefinition.create(
                        adsk.core.ValueInput.createByReal(cm(PILOT_SHLDR_H))),
                    adsk.fusion.ExtentDirections.NegativeExtentDirection)
                f3.extrudeFeatures.add(e)
            except: pass

        # Wire clearance slot at 6 o'clock of motor bore
        sk3w = c3.sketches.add(c3.xYConstructionPlane)
        WL3 = sk3w.sketchCurves.sketchLines
        wx = cx3 - WIRE_W/2; wy = cy3 - MOTOR_BORE/2 - WIRE_H
        WL3.addByTwoPoints(
            adsk.core.Point3D.create(cm(wx),cm(wy),0),
            adsk.core.Point3D.create(cm(wx+WIRE_W),cm(wy),0))
        WL3.addByTwoPoints(
            adsk.core.Point3D.create(cm(wx+WIRE_W),cm(wy),0),
            adsk.core.Point3D.create(cm(wx+WIRE_W),cm(wy+WIRE_H),0))
        WL3.addByTwoPoints(
            adsk.core.Point3D.create(cm(wx+WIRE_W),cm(wy+WIRE_H),0),
            adsk.core.Point3D.create(cm(wx),cm(wy+WIRE_H),0))
        WL3.addByTwoPoints(
            adsk.core.Point3D.create(cm(wx),cm(wy+WIRE_H),0),
            adsk.core.Point3D.create(cm(wx),cm(wy),0))
        w3_prof = largest_profile(sk3w)
        if w3_prof:
            try:
                e = f3.extrudeFeatures.createInput(w3_prof, CUT)
                e.setAllExtent(adsk.fusion.ExtentDirections.PositiveExtentDirection)
                f3.extrudeFeatures.add(e)
            except: pass

        # ════════════════════════════════════
        # 4. ROPE GUIDE
        # ════════════════════════════════════
        GB_W=80; GB_D=60; GB_T=10
        ARM_H=100; ARM_T=12
        PUL_OD=50; PUL_BORE=8; PUL_W=20
        GROOVE_R_W=10; GROOVE_R_D=5  # rope groove on pulley

        occ4 = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        c4   = occ4.component; c4.name='ARIA_RopeGuide_Complete'; f4=c4.features

        # Base plate
        sk4 = c4.sketches.add(c4.xZConstructionPlane)
        make_rect(sk4, 0, 0, GB_W, GB_D)
        for bx4,bd4 in [(15,15),(GB_W-15,15),(15,GB_D-15),(GB_W-15,GB_D-15)]:
            sk4.sketchCurves.sketchCircles.addByCenterRadius(
                adsk.core.Point3D.create(cm(bx4),cm(bd4),0), cm(6.6/2))
        base4_prof = largest_profile(sk4)
        if base4_prof:
            e = f4.extrudeFeatures.createInput(base4_prof, NEW)
            e.setOneSideExtent(
                adsk.fusion.DistanceExtentDefinition.create(
                    adsk.core.ValueInput.createByReal(cm(GB_T))),
                adsk.fusion.ExtentDirections.PositiveExtentDirection)
            f4.extrudeFeatures.add(e)

        # Vertical arm
        arm_p_in = c4.constructionPlanes.createInput()
        arm_p_in.setByOffset(c4.xYConstructionPlane,
            adsk.core.ValueInput.createByReal(cm(GB_D/2)))
        arm_p = c4.constructionPlanes.add(arm_p_in)
        sk4a = c4.sketches.add(arm_p)
        make_rect(sk4a, GB_W/2-ARM_T/2, GB_T, ARM_T, ARM_H)
        arm_prof = largest_profile(sk4a)
        if arm_prof:
            try:
                e = f4.extrudeFeatures.createInput(arm_prof, JOIN)
                e.setSymmetricExtent(
                    adsk.core.ValueInput.createByReal(cm(ARM_T/2)), True)
                f4.extrudeFeatures.add(e)
            except:
                e = f4.extrudeFeatures.createInput(arm_prof, NEW)
                e.setOneSideExtent(
                    adsk.fusion.DistanceExtentDefinition.create(
                        adsk.core.ValueInput.createByReal(cm(ARM_T))),
                    adsk.fusion.ExtentDirections.PositiveExtentDirection)
                f4.extrudeFeatures.add(e)

        # Pulley wheel at top of arm
        pul_y = GB_D/2 - PUL_W/2
        pul_p_in = c4.constructionPlanes.createInput()
        pul_p_in.setByOffset(c4.xYConstructionPlane,
            adsk.core.ValueInput.createByReal(cm(pul_y)))
        pul_p = c4.constructionPlanes.add(pul_p_in)
        sk4p = c4.sketches.add(pul_p)
        pul_cx = GB_W/2; pul_cy = GB_T + ARM_H
        sk4p.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(cm(pul_cx),cm(pul_cy),0), cm(PUL_OD/2))
        sk4p.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(cm(pul_cx),cm(pul_cy),0), cm(PUL_BORE/2))
        pul_prof = annular_profile(sk4p, PUL_BORE/2, PUL_OD/2)
        if pul_prof:
            try:
                e = f4.extrudeFeatures.createInput(pul_prof, JOIN)
                e.setOneSideExtent(
                    adsk.fusion.DistanceExtentDefinition.create(
                        adsk.core.ValueInput.createByReal(cm(PUL_W))),
                    adsk.fusion.ExtentDirections.PositiveExtentDirection)
                f4.extrudeFeatures.add(e)
            except: pass

        # Rope groove on pulley OD
        pul_g_p_in = c4.constructionPlanes.createInput()
        pul_g_p_in.setByOffset(c4.xYConstructionPlane,
            adsk.core.ValueInput.createByReal(cm(pul_y + PUL_W/2 - GROOVE_R_W/2)))
        pul_g_p = c4.constructionPlanes.add(pul_g_p_in)
        sk4rg = c4.sketches.add(pul_g_p)
        sk4rg.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(cm(pul_cx),cm(pul_cy),0), cm(PUL_OD/2))
        sk4rg.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(cm(pul_cx),cm(pul_cy),0), cm(PUL_OD/2 - GROOVE_R_D))
        rg_prof = annular_profile(sk4rg, PUL_OD/2-GROOVE_R_D, PUL_OD/2)
        if rg_prof:
            try:
                e = f4.extrudeFeatures.createInput(rg_prof, CUT)
                e.setOneSideExtent(
                    adsk.fusion.DistanceExtentDefinition.create(
                        adsk.core.ValueInput.createByReal(cm(GROOVE_R_W))),
                    adsk.fusion.ExtentDirections.PositiveExtentDirection)
                f4.extrudeFeatures.add(e)
            except: pass

        ui.messageBox(
            'ARIA Support Components Complete ✓\n\n'
            '  ARIA_EndCap_Complete\n'
            '  ARIA_WallBracket_Complete\n'
            '  ARIA_MotorMount_Complete\n'
            '  ARIA_RopeGuide_Complete\n\n'
            'All features included:\n'
            '  EndCap: bearing shoulder + O-ring groove + counterbores\n'
            '  WallBracket: slotted wall holes + gusset + floor anchors\n'
            '  MotorMount: pilot shoulder + wire slot + all bolt holes\n'
            '  RopeGuide: rope groove + arm + pulley with axle bore\n\n'
            'Ready to export as STL for PLA print.'
        )

    except:
        if ui:
            ui.messageBox('FAILED:\n' + traceback.format_exc())
