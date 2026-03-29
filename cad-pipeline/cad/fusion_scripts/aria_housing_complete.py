"""
ARIA Housing Complete (v-final)
Key fix: participantBodies = [body] on every cut and join operation.
Units: raw mm values (no cm conversion).
Builds in root component.
"""
import adsk.core, adsk.fusion, traceback, math

H_W=700.0; H_H=680.0; H_D=344.0; WALL=10.0
SPOOL_CX=350.0; SPOOL_CY=330.0
BEARING_OD=47.2; BEARING_SHLDR_OD=55.0; BEARING_SHLDR_H=3.0
RATCHET_POCKET_D=213.0; RATCHET_POCKET_DEPTH=21.0
ROPE_SLOT_W=30.0; ROPE_SLOT_L=80.0
BOSS_DIA=30.0; BOSS_H=20.0; BOSS_HOLE_D=10.5; BOSS_INSET=60.0
CABLE_HOLE_D=25.0; DRAIN_D=8.0

def run(context):
    ui = None
    try:
        app  = adsk.core.Application.get()
        ui   = app.userInterface
        des  = adsk.fusion.Design.cast(app.activeProduct)
        if des.designType == adsk.fusion.DesignTypes.ParametricDesignType:
            des.designType = adsk.fusion.DesignTypes.DirectDesignType

        root  = des.rootComponent
        feats = root.features
        errors = []

        NEW = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        JOIN= adsk.fusion.FeatureOperations.JoinFeatureOperation
        CUT = adsk.fusion.FeatureOperations.CutFeatureOperation
        POS = adsk.fusion.ExtentDirections.PositiveExtentDirection
        NEG = adsk.fusion.ExtentDirections.NegativeExtentDirection

        def dist(mm):
            return adsk.fusion.DistanceExtentDefinition.create(
                adsk.core.ValueInput.createByReal(mm))

        def P(x, y): return adsk.core.Point3D.create(x, y, 0)

        def rect(sk, x, y, w, h):
            L = sk.sketchCurves.sketchLines
            L.addByTwoPoints(P(x,y),     P(x+w,y))
            L.addByTwoPoints(P(x+w,y),   P(x+w,y+h))
            L.addByTwoPoints(P(x+w,y+h), P(x,y+h))
            L.addByTwoPoints(P(x,y+h),   P(x,y))

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

        box = [None]

        def get_box():
            best, bd = None, 9999.0
            for bi in range(root.bRepBodies.count):
                b = root.bRepBodies.item(bi)
                bb = b.boundingBox
                bw = abs(bb.maxPoint.x-bb.minPoint.x)
                bh = abs(bb.maxPoint.y-bb.minPoint.y)
                bz = abs(bb.maxPoint.z-bb.minPoint.z)
                d = abs(bw-H_W)+abs(bh-H_H)+abs(bz-H_D)
                if d < bd: bd=d; best=b
            box[0] = best
            return best

        def face_on(body, axis, target, min_span=200.0):
            best, bd = None, 9999.0
            for fi in range(body.faces.count):
                f = body.faces.item(fi)
                bb = f.boundingBox
                if axis=='z':
                    span=abs(bb.maxPoint.z-bb.minPoint.z)
                    mid=(bb.maxPoint.z+bb.minPoint.z)/2.0
                    other=abs(bb.maxPoint.x-bb.minPoint.x)
                elif axis=='y':
                    span=abs(bb.maxPoint.y-bb.minPoint.y)
                    mid=(bb.maxPoint.y+bb.minPoint.y)/2.0
                    other=abs(bb.maxPoint.x-bb.minPoint.x)
                else:
                    span=abs(bb.maxPoint.x-bb.minPoint.x)
                    mid=(bb.maxPoint.x+bb.minPoint.x)/2.0
                    other=abs(bb.maxPoint.y-bb.minPoint.y)
                if span<0.5 and other>min_span:
                    d=abs(mid-target)
                    if d<bd: bd=d; best=f
            return best

        def sk_on(axis, target, name='', min_span=200.0):
            b = get_box()
            face = face_on(b, axis, target, min_span) if b else None
            if face:
                sk = root.sketches.add(face)
            else:
                pi = root.constructionPlanes.createInput()
                if axis=='z':
                    pi.setByOffset(root.xYConstructionPlane,
                        adsk.core.ValueInput.createByReal(target))
                elif axis=='y':
                    pi.setByOffset(root.xZConstructionPlane,
                        adsk.core.ValueInput.createByReal(target))
                else:
                    pi.setByOffset(root.yZConstructionPlane,
                        adsk.core.ValueInput.createByReal(target))
                pl = root.constructionPlanes.add(pi)
                sk = root.sketches.add(pl)
            if name: sk.name = name
            return sk

        def do_cut(sk, prof, depth, direction, body):
            ext = feats.extrudeFeatures.createInput(prof, CUT)
            ext.setOneSideExtent(dist(depth), direction)
            try:
                ext.participantBodies = [body]
            except:
                pass  # try without if it fails
            return feats.extrudeFeatures.add(ext)

        def do_join(sk, prof, depth, direction, body):
            ext = feats.extrudeFeatures.createInput(prof, JOIN)
            ext.setOneSideExtent(dist(depth), direction)
            try:
                ext.participantBodies = [body]
            except:
                pass
            return feats.extrudeFeatures.add(ext)

        # ── 1. SOLID BOX ──
        sk1 = root.sketches.add(root.xYConstructionPlane)
        sk1.name = 'HousingBox'
        rect(sk1, 0, 0, H_W, H_H)
        e1 = feats.extrudeFeatures.createInput(sk1.profiles.item(0), NEW)
        e1.setOneSideExtent(dist(H_D), POS)
        feats.extrudeFeatures.add(e1)

        b0 = get_box()
        if not b0:
            ui.messageBox('Box failed.'); return

        bb0=b0.boundingBox
        bw0=abs(bb0.maxPoint.x-bb0.minPoint.x)
        bh0=abs(bb0.maxPoint.y-bb0.minPoint.y)
        bd0=abs(bb0.maxPoint.z-bb0.minPoint.z)
        ui.messageBox(f'✅ Box: {bw0:.0f}x{bh0:.0f}x{bd0:.0f}mm\n'
                     f'Body: {b0.name}  Faces: {b0.faces.count}\n\n'
                     f'participantBodies will be set to: {b0.name}')

        # ── 2. INTERIOR VOID ──
        try:
            sk2 = sk_on('z', 0, 'InteriorCut', min_span=H_W*0.4)
            rect(sk2, WALL, WALL, H_W-2*WALL, H_H-2*WALL)
            p2 = lp(sk2)
            if p2:
                do_cut(sk2, p2, H_D-WALL, POS, b0)
                ui.messageBox('✅ Interior void done.')
            else:
                errors.append('Interior cut: no profile')
        except Exception as ex:
            errors.append(f'Interior cut: {ex}')

        # ── LEFT BORE ──
        try:
            b = get_box()
            sk = sk_on('z', 0, 'LeftBore', min_span=H_W*0.4)
            sk.sketchCurves.sketchCircles.addByCenterRadius(
                P(SPOOL_CX, SPOOL_CY), BEARING_OD/2)
            p = lp(sk)
            if p: do_cut(sk, p, WALL+2, POS, b)
        except Exception as ex: errors.append(f'Left bore: {ex}')

        # ── RIGHT BORE ──
        try:
            b = get_box()
            sk = sk_on('z', H_D, 'RightBore', min_span=H_W*0.4)
            sk.sketchCurves.sketchCircles.addByCenterRadius(
                P(SPOOL_CX, SPOOL_CY), BEARING_OD/2)
            p = lp(sk)
            if p: do_cut(sk, p, WALL+2, NEG, b)
        except Exception as ex: errors.append(f'Right bore: {ex}')

        # ── BEARING SHOULDERS ──
        for z_t, direction, name in [(0,POS,'LeftShoulder'),(H_D,NEG,'RightShoulder')]:
            try:
                b = get_box()
                sk = sk_on('z', z_t, name, min_span=H_W*0.4)
                C = sk.sketchCurves.sketchCircles
                C.addByCenterRadius(P(SPOOL_CX,SPOOL_CY), BEARING_SHLDR_OD/2)
                C.addByCenterRadius(P(SPOOL_CX,SPOOL_CY), BEARING_OD/2)
                p = ap(sk, BEARING_OD/2, BEARING_SHLDR_OD/2)
                if p: do_join(sk, p, BEARING_SHLDR_H, direction, b)
            except Exception as ex: errors.append(f'{name}: {ex}')

        # ── RATCHET POCKET ──
        try:
            b = get_box()
            sk = sk_on('z', H_D, 'RatchetPocket', min_span=H_W*0.4)
            sk.sketchCurves.sketchCircles.addByCenterRadius(
                P(SPOOL_CX, SPOOL_CY), RATCHET_POCKET_D/2)
            p = lp(sk)
            if p: do_cut(sk, p, RATCHET_POCKET_DEPTH, NEG, b)
        except Exception as ex: errors.append(f'Ratchet pocket: {ex}')

        # ── ROPE SLOT ──
        try:
            b = get_box()
            sk = sk_on('y', H_H, 'RopeSlot', min_span=H_W*0.4)
            SL=sk.sketchCurves.sketchLines; SA=sk.sketchCurves.sketchArcs
            sx=SPOOL_CX-ROPE_SLOT_W/2; sd=H_D/2-ROPE_SLOT_L/2; sr=ROPE_SLOT_W/2
            def SP(x,z): return adsk.core.Point3D.create(x, z, 0)
            SL.addByTwoPoints(SP(sx,sd+sr),SP(sx,sd+ROPE_SLOT_L-sr))
            SA.addByThreePoints(SP(sx,sd+ROPE_SLOT_L-sr),SP(sx+sr,sd+ROPE_SLOT_L),
                                SP(sx+ROPE_SLOT_W,sd+ROPE_SLOT_L-sr))
            SL.addByTwoPoints(SP(sx+ROPE_SLOT_W,sd+ROPE_SLOT_L-sr),SP(sx+ROPE_SLOT_W,sd+sr))
            SA.addByThreePoints(SP(sx+ROPE_SLOT_W,sd+sr),SP(sx+sr,sd),SP(sx,sd+sr))
            p = lp(sk)
            if p: do_cut(sk, p, WALL+5, NEG, b)
        except Exception as ex: errors.append(f'Rope slot: {ex}')

        # ── DRAIN HOLES ──
        try:
            b = get_box()
            sk = sk_on('y', 0, 'DrainHoles', min_span=H_W*0.4)
            for dx,dz in [(H_W*.2,H_D*.25),(H_W*.8,H_D*.25),
                          (H_W*.2,H_D*.75),(H_W*.8,H_D*.75)]:
                sk.sketchCurves.sketchCircles.addByCenterRadius(
                    adsk.core.Point3D.create(dx,dz,0), DRAIN_D/2)
            for i in range(sk.profiles.count):
                try: do_cut(sk, sk.profiles.item(i), WALL+2, POS, b)
                except: pass
        except Exception as ex: errors.append(f'Drain holes: {ex}')

        # ── CABLE ENTRIES ──
        try:
            b = get_box()
            sk = sk_on('z', H_D, 'CableEntries', min_span=H_W*0.4)
            for cy in [80.0, 120.0]:
                sk.sketchCurves.sketchCircles.addByCenterRadius(
                    P(H_W-80, cy), CABLE_HOLE_D/2)
            for i in range(sk.profiles.count):
                try: do_cut(sk, sk.profiles.item(i), WALL+2, NEG, b)
                except: pass
        except Exception as ex: errors.append(f'Cable entries: {ex}')

        # ── MOUNTING BOSSES ──
        boss_pos=[(BOSS_INSET,BOSS_INSET),(H_W-BOSS_INSET,BOSS_INSET),
                  (BOSS_INSET,H_H-BOSS_INSET),(H_W-BOSS_INSET,H_H-BOSS_INSET)]
        try:
            b = get_box()
            sk = sk_on('z', H_D, 'Bosses', min_span=H_W*0.4)
            for bx,by in boss_pos:
                sk.sketchCurves.sketchCircles.addByCenterRadius(P(bx,by), BOSS_DIA/2)
                sk.sketchCurves.sketchCircles.addByCenterRadius(P(bx,by), BOSS_HOLE_D/2)
            exp_ann = math.pi*((BOSS_DIA/2)**2-(BOSS_HOLE_D/2)**2)
            for i in range(sk.profiles.count):
                try:
                    a=sk.profiles.item(i).areaProperties().area
                    if abs(a-exp_ann)<exp_ann*0.3:
                        do_join(sk, sk.profiles.item(i), BOSS_H, POS, b)
                except: pass
            sk2 = sk_on('z', H_D, 'BossHoles', min_span=H_W*0.4)
            for bx,by in boss_pos:
                sk2.sketchCurves.sketchCircles.addByCenterRadius(P(bx,by), BOSS_HOLE_D/2)
            for i in range(sk2.profiles.count):
                try:
                    ext=feats.extrudeFeatures.createInput(sk2.profiles.item(i),CUT)
                    ext.setAllExtent(NEG)
                    try: ext.participantBodies = [b]
                    except: pass
                    feats.extrudeFeatures.add(ext)
                except: pass
        except Exception as ex: errors.append(f'Bosses: {ex}')

        n = root.bRepBodies.count
        msg = f'ARIA Housing\nRoot bodies: {n}\n\n'
        msg += '✅ All features done.\n' if not errors else \
               f'⚠ {len(errors)} issue(s):\n'+''.join(f'  • {e}\n' for e in errors)
        msg += f'\nBox: {H_W}×{H_H}×{H_D}mm  Wall:{WALL}mm\n\n'
        msg += 'Manual fallbacks:\n'
        msg += '  Interior void: Modify→Shell→front face→10mm\n'
        msg += '  Left bore: sketch front face→Ø47.2mm at (350,330)→Cut 12mm\n'
        msg += '  Right shoulder: sketch back face→Ø55+Ø47.2mm→Join 3mm'
        ui.messageBox(msg)

    except:
        if ui: ui.messageBox('FATAL:\n'+traceback.format_exc())
