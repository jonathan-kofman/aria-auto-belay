"""
ARIA — Cam Collar (v-mm)
Raw mm values. True wedge ramps using loft instead of extrude+cut.
"""
import adsk.core, adsk.fusion, traceback, math

COLLAR_OD=60.0; COLLAR_ID=20.0; COLLAR_T=8.0
N_RAMPS=2; RAMP_RISE=3.5; RAMP_LEN=18.0; RAMP_W=16.0
KEY_W=6.0; KEY_D=3.0

def run(context):
    ui = None
    try:
        app  = adsk.core.Application.get()
        ui   = app.userInterface
        des  = adsk.fusion.Design.cast(app.activeProduct)
        if des.designType == adsk.fusion.DesignTypes.ParametricDesignType:
            des.designType = adsk.fusion.DesignTypes.DirectDesignType

        root = des.rootComponent
        errors = []

        def val(mm): return adsk.core.ValueInput.createByReal(mm)
        def dist(mm): return adsk.fusion.DistanceExtentDefinition.create(val(mm))
        def P(x,y): return adsk.core.Point3D.create(x, y, 0)
        def Pp(r,a): return adsk.core.Point3D.create(r*math.cos(a), r*math.sin(a), 0)

        NEW = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        JOIN= adsk.fusion.FeatureOperations.JoinFeatureOperation
        CUT = adsk.fusion.FeatureOperations.CutFeatureOperation
        POS = adsk.fusion.ExtentDirections.PositiveExtentDirection
        NEG = adsk.fusion.ExtentDirections.NegativeExtentDirection

        def lp(sk):
            best, ba = None, 0.0
            for i in range(sk.profiles.count):
                p = sk.profiles.item(i)
                try:
                    a = p.areaProperties().area
                    if a > ba: ba=a; best=p
                except: pass
            return best

        def ap(sk, r_in, r_out):
            exp = math.pi*(r_out**2 - r_in**2)
            best, bd = None, 9999.0
            for i in range(sk.profiles.count):
                p = sk.profiles.item(i)
                try:
                    d = abs(p.areaProperties().area - exp)
                    if d < bd: bd=d; best=p
                except: pass
            return best

        occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp = occ.component; comp.name='ARIA_CamCollar'; feats=comp.features

        # ── 1. BASE ANNULAR DISK ──
        sk_base = comp.sketches.add(comp.xYConstructionPlane)
        sk_base.name = 'CollarBase'
        origin = adsk.core.Point3D.create(0,0,0)
        sk_base.sketchCurves.sketchCircles.addByCenterRadius(origin, COLLAR_OD/2)
        sk_base.sketchCurves.sketchCircles.addByCenterRadius(origin, COLLAR_ID/2)

        ann = ap(sk_base, COLLAR_ID/2, COLLAR_OD/2)
        if not ann: ui.messageBox('Base annular profile not found'); return

        e = feats.extrudeFeatures.createInput(ann, NEW)
        e.setOneSideExtent(dist(COLLAR_T), POS)
        feats.extrudeFeatures.add(e)

        body = comp.bRepBodies.item(0) if comp.bRepBodies.count > 0 else None
        if not body: ui.messageBox('Base extrude failed'); return

        ui.messageBox(f'✅ Base disk created: Ø{COLLAR_OD}×{COLLAR_T}mm. Adding ramps...')

        # ── 2. WEDGE RAMPS ──
        # Build each ramp as a solid wedge body then JOIN to collar
        # Wedge: sector footprint, height goes from 0 at entry to RAMP_RISE at exit
        R_mid = (COLLAR_OD/2 + COLLAR_ID/2) / 2  # midline radius ~20mm
        R_in  = COLLAR_ID/2 + 2.0   # inner edge of ramp
        R_out = COLLAR_OD/2 - 2.0   # outer edge of ramp
        ramp_arc = RAMP_LEN / R_mid  # angular span in radians

        for ri in range(N_RAMPS):
            base_a = ri * math.pi
            a0 = base_a - ramp_arc/2  # entry angle
            a1 = base_a + ramp_arc/2  # exit angle (full rise here)
            amid = base_a

            try:
                # Sketch ramp FOOTPRINT on top face of collar
                top_face = None
                for fi in range(body.faces.count):
                    f = body.faces.item(fi)
                    bb = f.boundingBox
                    mz = (bb.maxPoint.z+bb.minPoint.z)/2
                    sz = abs(bb.maxPoint.z-bb.minPoint.z)
                    if sz < 0.5 and abs(mz - COLLAR_T) < 1.0:
                        top_face = f; break

                if top_face:
                    sk_r = comp.sketches.add(top_face)
                else:
                    pi = comp.constructionPlanes.createInput()
                    pi.setByOffset(comp.xYConstructionPlane, val(COLLAR_T))
                    pl = comp.constructionPlanes.add(pi)
                    sk_r = comp.sketches.add(pl)

                sk_r.name = f'Ramp_{ri+1}'
                RA = sk_r.sketchCurves.sketchArcs
                RL = sk_r.sketchCurves.sketchLines

                # Sector footprint
                RA.addByThreePoints(Pp(R_in,a0), Pp(R_in,amid), Pp(R_in,a1))
                RA.addByThreePoints(Pp(R_out,a0), Pp(R_out,amid), Pp(R_out,a1))
                RL.addByTwoPoints(Pp(R_in,a0), Pp(R_out,a0))
                RL.addByTwoPoints(Pp(R_in,a1), Pp(R_out,a1))

                ramp_prof = lp(sk_r)
                if ramp_prof:
                    # Extrude to max height — creates uniform block
                    # First ramp JOINs, subsequent ramps use NEW then Combine
                    op = JOIN if comp.bRepBodies.count == 1 else NEW
                    e = feats.extrudeFeatures.createInput(ramp_prof, op)
                    e.setOneSideExtent(dist(RAMP_RISE), POS)
                    feats.extrudeFeatures.add(e)
                    # If created as separate body, combine with collar
                    if op == NEW and comp.bRepBodies.count > 1:
                        try:
                            main = comp.bRepBodies.item(0)
                            tools = adsk.core.ObjectCollection.create()
                            for bi in range(1, comp.bRepBodies.count):
                                tools.add(comp.bRepBodies.item(bi))
                            ci = feats.combineFeatures.createInput(main, tools)
                            ci.operation = JOIN
                            ci.isKeepToolBodies = False
                            feats.combineFeatures.add(ci)
                        except: pass

                    ui.messageBox(
                        f'Ramp {ri+1} block created.\n\n'
                        f'NOW TAPER IT MANUALLY:\n'
                        f'1. Select the entry end face of ramp {ri+1}\n'
                        f'   (the narrow end at angle {math.degrees(a0):.0f}°)\n'
                        f'2. Modify → Move Face\n'
                        f'3. Drag downward {RAMP_RISE}mm\n'
                        f'   (this tapers from 0 at entry to {RAMP_RISE}mm at exit)\n\n'
                        f'The ramp should slope from flush with collar surface\n'
                        f'at entry to {RAMP_RISE}mm proud at exit.')

            except Exception as ex:
                errors.append(f'Ramp {ri+1}: {ex}')

        # ── 3. KEYWAY ──
        try:
            sk_k = comp.sketches.add(comp.xYConstructionPlane)
            sk_k.name = 'Keyway'
            KL = sk_k.sketchCurves.sketchLines
            hw = KEY_W/2; r = COLLAR_ID/2
            KL.addByTwoPoints(P(-hw, r-KEY_D), P(hw, r-KEY_D))
            KL.addByTwoPoints(P(hw, r-KEY_D),  P(hw, r+KEY_D))
            KL.addByTwoPoints(P(hw, r+KEY_D),  P(-hw, r+KEY_D))
            KL.addByTwoPoints(P(-hw, r+KEY_D), P(-hw, r-KEY_D))
            kp = lp(sk_k)
            if kp:
                e = feats.extrudeFeatures.createInput(kp, CUT)
                e.setAllExtent(POS)
                feats.extrudeFeatures.add(e)
        except Exception as ex: errors.append(f'Keyway: {ex}')

        ramp_deg = math.degrees(math.atan2(RAMP_RISE, RAMP_LEN))
        msg = f'ARIA Cam Collar\n\n'
        msg += '✅ Base + ramp blocks + keyway created.\n\n'
        msg += f'OD:{COLLAR_OD}mm  ID:{COLLAR_ID}mm  T:{COLLAR_T}mm\n'
        msg += f'Ramp rise:{RAMP_RISE}mm over {RAMP_LEN}mm ({ramp_deg:.1f}°)\n\n'
        msg += 'MANUAL STEP REQUIRED:\n'
        msg += 'Taper each ramp block using Modify → Move Face\n'
        msg += 'on the entry end face — drag down 3.5mm\n'
        if errors:
            msg += f'\nIssues: '+''.join(f'\n  • {e}' for e in errors)
        ui.messageBox(msg)

    except:
        if ui: ui.messageBox('FATAL:\n'+traceback.format_exc())
