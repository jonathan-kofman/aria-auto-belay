"""
ARIA — Ratchet Ring + Main Shaft (v-mm)
All values in raw mm — no cm() conversion.
Ratchet Ring: 24 asymmetric teeth, bolt holes, counterbores, root fillets
Main Shaft: Ø20mm, keyway, shoulder step, circlip groove
"""
import adsk.core, adsk.fusion, traceback, math

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

        # ════════════════════════════════════
        # 1. RATCHET RING
        # ════════════════════════════════════
        Rp=100.0; ha=6.0; hd=3.0
        Rtip=Rp+ha; Rroot=Rp-hd; RID=Rroot-12.0; FACE_W=20.0
        N_T=24; DRIVE_DEG=8.0; BACK_DEG=60.0
        BCD_R=85.0; N_BOLTS=6; BOLT_D=6.6; CBORE_D=11.0; CBORE_DEPTH=6.0

        occ1 = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        c1   = occ1.component; c1.name='ARIA_RatchetRing'; f1=c1.features

        # ── Ring body via revolve ──
        # Profile: rectangle in XY plane, X=radius axis, Y=axial axis
        sk1 = c1.sketches.add(c1.xYConstructionPlane)
        sk1.name = 'RingProfile'
        L1 = sk1.sketchCurves.sketchLines
        L1.addByTwoPoints(P(RID,0),      P(Rroot,0))
        L1.addByTwoPoints(P(Rroot,0),    P(Rroot,FACE_W))
        L1.addByTwoPoints(P(Rroot,FACE_W), P(RID,FACE_W))
        L1.addByTwoPoints(P(RID,FACE_W), P(RID,0))

        rp = lp(sk1)
        if rp:
            rev = f1.revolveFeatures.createInput(rp, c1.yConstructionAxis, NEW)
            rev.setAngleExtent(False, adsk.core.ValueInput.createByReal(2*math.pi))
            f1.revolveFeatures.add(rev)
        else:
            ui.messageBox('Ring profile not found'); return

        # ── One tooth ──
        circ_pitch = 2*math.pi*Rp/N_T  # 26.18mm
        half_ang   = (circ_pitch/2)/Rp  # radians

        # Drive side (steep face, ~8° from radial)
        fd = half_ang + math.pi/2 - math.radians(DRIVE_DEG)
        pd_x=Rp*math.cos(half_ang); pd_y=Rp*math.sin(half_ang)
        td_x=pd_x+ha*2*math.cos(fd); td_y=pd_y+ha*2*math.sin(fd)
        m=math.sqrt(td_x**2+td_y**2); td_x=td_x/m*Rtip; td_y=td_y/m*Rtip

        # Back side (shallow face, ~60° from radial)
        fb = -half_ang + math.pi/2 + math.radians(BACK_DEG)
        pb_x=Rp*math.cos(-half_ang); pb_y=Rp*math.sin(-half_ang)
        tb_x=pb_x+ha*2*math.cos(fb); tb_y=pb_y+ha*2*math.sin(fb)
        m=math.sqrt(tb_x**2+tb_y**2); tb_x=tb_x/m*Rtip; tb_y=tb_y/m*Rtip

        # Root points
        re=0.3
        rd_x=Rroot*math.cos(half_ang+re); rd_y=Rroot*math.sin(half_ang+re)
        rb_x=Rroot*math.cos(-half_ang-re); rb_y=Rroot*math.sin(-half_ang-re)

        sk_t = c1.sketches.add(c1.xZConstructionPlane)
        sk_t.name = 'ToothProfile'
        TL=sk_t.sketchCurves.sketchLines
        TA=sk_t.sketchCurves.sketchArcs
        TL.addByTwoPoints(P(rd_x,rd_y),  P(pd_x,pd_y))
        TL.addByTwoPoints(P(pd_x,pd_y),  P(td_x,td_y))
        TL.addByTwoPoints(P(td_x,td_y),  P(tb_x,tb_y))
        TL.addByTwoPoints(P(tb_x,tb_y),  P(pb_x,pb_y))
        TL.addByTwoPoints(P(pb_x,pb_y),  P(rb_x,rb_y))
        TA.addByThreePoints(P(rd_x,rd_y), P(Rroot,0), P(rb_x,rb_y))

        tp = lp(sk_t)
        if tp:
            try:
                e = f1.extrudeFeatures.createInput(tp, JOIN)
                e.setOneSideExtent(dist(FACE_W), POS)
                f1.extrudeFeatures.add(e)

                # Circular pattern 24x around Y axis
                bodies = adsk.core.ObjectCollection.create()
                for bi in range(c1.bRepBodies.count):
                    bodies.add(c1.bRepBodies.item(bi))
                pat = f1.circularPatternFeatures.createInput(bodies, c1.yConstructionAxis)
                pat.quantity = adsk.core.ValueInput.createByReal(N_T)
                pat.totalAngle = adsk.core.ValueInput.createByReal(2*math.pi)
                pat.isSymmetric = False
                f1.circularPatternFeatures.add(pat)
            except Exception as ex:
                errors.append(f'Tooth/pattern: {ex}')
        else:
            errors.append('Tooth profile not found — add teeth manually')

        # ── Bolt holes ──
        try:
            sk_b = c1.sketches.add(c1.xZConstructionPlane)
            sk_b.name = 'BoltHoles'
            for i in range(N_BOLTS):
                a = i*2*math.pi/N_BOLTS
                sk_b.sketchCurves.sketchCircles.addByCenterRadius(
                    Pp(BCD_R,a), BOLT_D/2)
            for i in range(sk_b.profiles.count):
                try:
                    e=f1.extrudeFeatures.createInput(sk_b.profiles.item(i),CUT)
                    e.setAllExtent(POS)
                    f1.extrudeFeatures.add(e)
                except: pass
        except Exception as ex: errors.append(f'Bolt holes: {ex}')

        # ── Counterbores ──
        try:
            back_face = None
            if c1.bRepBodies.count > 0:
                body = c1.bRepBodies.item(0)
                for fi in range(body.faces.count):
                    f = body.faces.item(fi)
                    bb = f.boundingBox
                    mid_y = (bb.maxPoint.y+bb.minPoint.y)/2
                    span_y = abs(bb.maxPoint.y-bb.minPoint.y)
                    if span_y < 0.5 and abs(mid_y-FACE_W) < 1.0:
                        back_face = f; break
            if back_face:
                sk_cb = c1.sketches.add(back_face)
            else:
                pi=c1.constructionPlanes.createInput()
                pi.setByOffset(c1.xZConstructionPlane, val(FACE_W))
                pl=c1.constructionPlanes.add(pi)
                sk_cb=c1.sketches.add(pl)
            sk_cb.name='Counterbores'
            for i in range(N_BOLTS):
                a=i*2*math.pi/N_BOLTS
                sk_cb.sketchCurves.sketchCircles.addByCenterRadius(Pp(BCD_R,a), CBORE_D/2)
            for i in range(sk_cb.profiles.count):
                try:
                    e=f1.extrudeFeatures.createInput(sk_cb.profiles.item(i),CUT)
                    e.setOneSideExtent(dist(CBORE_DEPTH), NEG)
                    f1.extrudeFeatures.add(e)
                except: pass
        except Exception as ex: errors.append(f'Counterbores: {ex}')

        # ── Root fillets ──
        try:
            if c1.bRepBodies.count > 0:
                body=c1.bRepBodies.item(0)
                edges=adsk.core.ObjectCollection.create()
                for ei in range(body.edges.count):
                    e=body.edges.item(ei)
                    bb=e.boundingBox
                    cx=(bb.maxPoint.x+bb.minPoint.x)/2
                    cz=(bb.maxPoint.z+bb.minPoint.z)/2
                    r=math.sqrt(cx**2+cz**2)
                    if abs(r-Rroot)<3.0:
                        edges.add(e)
                if edges.count>0:
                    fi2=f1.filletFeatures.createInput()
                    fi2.addConstantRadiusEdgeSet(edges, val(1.5), True)
                    f1.filletFeatures.add(fi2)
        except: pass

        # ════════════════════════════════════
        # 2. MAIN SHAFT
        # ════════════════════════════════════
        SHAFT_D=20.0; SHAFT_L=80.0; KEY_W=6.0; KEY_D=3.0
        SHLDR_D=22.0; SHLDR_W=3.0; SHLDR_POS=30.0
        CLIP_D=18.0; CLIP_W=1.5; CLIP_POS=65.0

        occ2=root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        c2=occ2.component; c2.name='ARIA_MainShaft'; f2=c2.features

        # Shaft cylinder
        sk_sh=c2.sketches.add(c2.xYConstructionPlane)
        sk_sh.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(0,0,0), SHAFT_D/2)
        if sk_sh.profiles.count>0:
            e=f2.extrudeFeatures.createInput(sk_sh.profiles.item(0), NEW)
            e.setOneSideExtent(dist(SHAFT_L), POS)
            f2.extrudeFeatures.add(e)

        # Shoulder
        try:
            sh_face=None
            if c2.bRepBodies.count>0:
                body=c2.bRepBodies.item(0)
                for fi in range(body.faces.count):
                    f=body.faces.item(fi)
                    bb=f.boundingBox
                    mz=(bb.maxPoint.z+bb.minPoint.z)/2
                    sz=abs(bb.maxPoint.z-bb.minPoint.z)
                    r=(bb.maxPoint.x-bb.minPoint.x)/2
                    if sz<0.5 and abs(mz-SHLDR_POS)<2 and r>SHAFT_D/2*0.8:
                        sh_face=f; break
            if sh_face:
                sk_s=c2.sketches.add(sh_face)
            else:
                pi=c2.constructionPlanes.createInput()
                pi.setByOffset(c2.xYConstructionPlane,val(SHLDR_POS))
                pl=c2.constructionPlanes.add(pi)
                sk_s=c2.sketches.add(pl)
            sk_s.sketchCurves.sketchCircles.addByCenterRadius(
                adsk.core.Point3D.create(0,0,0), SHLDR_D/2)
            sk_s.sketchCurves.sketchCircles.addByCenterRadius(
                adsk.core.Point3D.create(0,0,0), SHAFT_D/2)
            sp=ap(sk_s, SHAFT_D/2, SHLDR_D/2)
            if sp:
                e=f2.extrudeFeatures.createInput(sp, JOIN)
                e.setOneSideExtent(dist(SHLDR_W), POS)
                f2.extrudeFeatures.add(e)
        except Exception as ex: errors.append(f'Shoulder: {ex}')

        # Circlip groove
        try:
            clip_face=None
            if c2.bRepBodies.count>0:
                body=c2.bRepBodies.item(0)
                for fi in range(body.faces.count):
                    f=body.faces.item(fi)
                    bb=f.boundingBox
                    mz=(bb.maxPoint.z+bb.minPoint.z)/2
                    sz=abs(bb.maxPoint.z-bb.minPoint.z)
                    if sz<0.5 and abs(mz-CLIP_POS)<5:
                        clip_face=f; break
            if clip_face:
                sk_cl=c2.sketches.add(clip_face)
            else:
                pi=c2.constructionPlanes.createInput()
                pi.setByOffset(c2.xYConstructionPlane,val(CLIP_POS))
                pl=c2.constructionPlanes.add(pi)
                sk_cl=c2.sketches.add(pl)
            sk_cl.sketchCurves.sketchCircles.addByCenterRadius(
                adsk.core.Point3D.create(0,0,0), SHAFT_D/2)
            sk_cl.sketchCurves.sketchCircles.addByCenterRadius(
                adsk.core.Point3D.create(0,0,0), CLIP_D/2)
            cp=ap(sk_cl, CLIP_D/2, SHAFT_D/2)
            if cp:
                e=f2.extrudeFeatures.createInput(cp, CUT)
                e.setOneSideExtent(dist(CLIP_W), POS)
                f2.extrudeFeatures.add(e)
        except Exception as ex: errors.append(f'Circlip: {ex}')

        # Keyway
        try:
            sk_k=c2.sketches.add(c2.xYConstructionPlane)
            sk_k.name='Keyway'
            KL=sk_k.sketchCurves.sketchLines
            hw=KEY_W/2; r=SHAFT_D/2
            KL.addByTwoPoints(P(-hw, r-KEY_D), P(hw, r-KEY_D))
            KL.addByTwoPoints(P(hw, r-KEY_D),  P(hw, r+KEY_D))
            KL.addByTwoPoints(P(hw, r+KEY_D),  P(-hw, r+KEY_D))
            KL.addByTwoPoints(P(-hw, r+KEY_D), P(-hw, r-KEY_D))
            kp=lp(sk_k)
            if kp:
                e=f2.extrudeFeatures.createInput(kp, CUT)
                e.setAllExtent(POS)
                f2.extrudeFeatures.add(e)
        except Exception as ex: errors.append(f'Keyway: {ex}')

        msg=f'ARIA Ratchet Ring + Shaft\n\n'
        msg+='✅ All done.\n' if not errors else \
             f'⚠ {len(errors)} issue(s):\n'+''.join(f'  • {e}\n' for e in errors)
        msg+=f'\nRatchet: Rp={Rp}mm, {N_T} teeth\nShaft: Ø{SHAFT_D}mm × {SHAFT_L}mm'
        ui.messageBox(msg)

    except:
        if ui: ui.messageBox('FATAL:\n'+traceback.format_exc())
