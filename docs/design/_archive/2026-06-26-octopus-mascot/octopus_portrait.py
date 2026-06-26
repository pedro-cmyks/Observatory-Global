#!/usr/bin/env python3
import math, random
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
random.seed(7)
W,H=520,600

def cub(p0,c1,c2,p3,t):
    u=1-t
    return (u*u*u*p0[0]+3*u*u*t*c1[0]+3*u*t*t*c2[0]+t*t*t*p3[0],
            u*u*u*p0[1]+3*u*u*t*c1[1]+3*u*t*t*c2[1]+t*t*t*p3[1])
def samp(segs,n=46):
    pts=[];per=max(2,n//len(segs))
    for si,(p0,c1,c2,p3) in enumerate(segs):
        for i in range(per+1):
            if si>0 and i==0: continue
            pts.append(cub(p0,c1,c2,p3,i/per))
    return pts
def norms(pts):
    o=[]
    for i in range(len(pts)):
        a=pts[max(0,i-1)];b=pts[min(len(pts)-1,i+1)]
        tx,ty=b[0]-a[0],b[1]-a[1];m=math.hypot(tx,ty) or 1
        o.append((-ty/m,tx/m,tx/m,ty/m))
    return o

MANTLE_SEGS=[((190,168),(190,116),(228,88),(260,88)),((260,88),(292,88),(330,116),(330,168)),
((330,168),(330,211),(317,250),(296,278)),((296,278),(283,295),(237,295),(224,278)),
((224,278),(203,250),(190,211),(190,168))]
ARMS=[
 ([((238,252),(176,262),(120,308),(132,366)),((132,366),(138,406),(178,408),(184,374))],22),
 ([((244,266),(222,326),(212,398),(226,470)),((226,470),(233,506),(256,500),(252,460))],27),
 ([((276,266),(298,326),(308,398),(294,470)),((294,470),(287,506),(264,500),(268,460))],27),
 ([((282,252),(344,262),(400,308),(388,366)),((388,366),(382,406),(342,408),(336,374))],22),
 ([((234,260),(180,292),(156,358),(170,420)),((170,420),(180,460),(214,454),(208,416))],26),
 ([((253,268),(247,344),(245,434),(253,520)),((253,520),(257,548),(272,545),(269,512))],28),
 ([((267,268),(273,344),(275,434),(267,520)),((267,520),(263,548),(248,545),(251,512))],28),
 ([((286,260),(340,292),(364,358),(350,420)),((350,420),(340,460),(306,454),(312,416))],26),
]
TIP=2.6
def arm_poly(segs,baseW):
    pts=samp(segs);no=norms(pts);n=len(pts);L=[];R=[]
    for i in range(n):
        t=i/(n-1);w=(TIP+(baseW-TIP)*(1-t)**1.05)/2;nx,ny,_,_=no[i]
        L.append((pts[i][0]+nx*w,pts[i][1]+ny*w));R.append((pts[i][0]-nx*w,pts[i][1]-ny*w))
    return L+R[::-1], pts, no, baseW

# geometry
polys=[]
mantle_pts=samp(MANTLE_SEGS,60)
polys.append(Polygon(mantle_pts).buffer(0))
polys.append(Polygon([ (260+72*math.cos(a),272+42*math.sin(a)) for a in [i/40*2*math.pi for i in range(40)] ]).buffer(0)) # web
arm_data=[]
for segs,bw in ARMS:
    poly,cpts,no,_=arm_poly(segs,bw)
    polys.append(Polygon(poly).buffer(0))
    arm_data.append((cpts,no,bw))
union=unary_union(polys)
if union.geom_type=="MultiPolygon":
    union=max(union.geoms,key=lambda g:g.area)
ext=list(union.exterior.coords)
UNION_D="M"+ "".join((("L" if i else "")+f"{x:.1f},{y:.1f}") for i,(x,y) in enumerate(ext))+"Z"
bd=union.exterior

def clamp(v): return max(0.0,min(1.0,v))
def sv(x,y):
    downness=clamp((y-150)/340)
    ld=clamp((((x-232)/210)+((y-170)/300))/2)
    base=0.2*downness+0.55*ld
    rim=clamp(1-bd.distance(Point(x,y))/27)
    return clamp(0.4*base+0.72*rim+0.04)

# hatching  (fn -> (color, opacity, width))
def hatch(angle,spacing,step,bow,fn):
    th=math.radians(angle);dx,dy=math.cos(th),math.sin(th);px,py=-math.sin(th),math.cos(th)
    cx,cy=260,330;R=320;out=[]
    o=-R
    while o<=R:
        bx,by=cx+px*o,cy+py*o
        run=[];t=-R
        while t<=R:
            x=bx+dx*t+px*bow*math.sin(math.pi*(t+R)/(2*R))
            y=by+dy*t+py*bow*math.sin(math.pi*(t+R)/(2*R))
            if union.contains(Point(x,y)):
                run.append((x,y))
            else:
                if len(run)>1: out.append(run)
                run=[]
            t+=step
        if len(run)>1: out.append(run)
        o+=spacing
    segs=""
    for run in out:
        s=sum(sv(x,y) for x,y in run)/len(run)
        col,op,wid=fn(s)
        if op<=0.02: continue
        d="M"+"".join((("L" if i else "")+f"{x:.1f},{y:.1f}") for i,(x,y) in enumerate(run))
        segs+=f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{wid:.2f}" opacity="{op:.2f}" stroke-linecap="round"/>'
    return segs

# ---- contour-following engraving ----
DARK="#02100a"
LIGHT="#bfe8d3"
# head: arcs wrapping the dome, denser toward the bottom/rim
def head_contour():
    cx,cy,rx,ry=260,178,73,95; out="";y=102
    while y<262:
        v=1-((y-cy)/ry)**2
        hw=rx*math.sqrt(v)*0.985 if v>0 else 0
        if hw>5:
            x0,x1=cx-hw,cx+hw; bow=4+(y-102)/160*7
            s=sv(cx,y+bow*0.5); op=0.10+0.48*s; wid=0.55+0.6*s
            out+=f'<path d="M{x0:.1f},{y:.1f} Q{cx:.1f},{y+bow:.1f} {x1:.1f},{y:.1f}" fill="none" stroke="{DARK}" stroke-width="{wid:.2f}" opacity="{op:.2f}" stroke-linecap="round"/>'
            if s<0.24:  # highlight arc on the lit upper-left
                out+=f'<path d="M{x0:.1f},{y-1.6:.1f} Q{cx:.1f},{y+bow-1.6:.1f} {x1:.1f},{y-1.6:.1f}" fill="none" stroke="{LIGHT}" stroke-width="0.6" opacity="0.12" stroke-linecap="round"/>'
        y+=4.4
    return out
# arms: cross-strokes ringing each tube + faint sucker rings
def arm_contour():
    out=""
    for cpts,no,bw in arm_data:
        n=len(cpts);cum=[0]
        for i in range(1,n): cum.append(cum[-1]+math.dist(cpts[i],cpts[i-1]))
        total=cum[-1]
        def at(s):
            for i in range(1,n):
                if cum[i]>=s:
                    f=(s-cum[i-1])/((cum[i]-cum[i-1])or 1)
                    return (cpts[i-1][0]+(cpts[i][0]-cpts[i-1][0])*f, cpts[i-1][1]+(cpts[i][1]-cpts[i-1][1])*f, no[i])
            return (cpts[-1][0],cpts[-1][1],no[-1])
        s=total*0.02
        while s<total*0.97:
            t=s/total; w=TIP+(bw-TIP)*(1-t)**1.05
            x,y,(nx,ny,tx,ty)=at(s)
            ax,ay=x+nx*w*0.5,y+ny*w*0.5; bx,by=x-nx*w*0.5,y-ny*w*0.5
            ctrlx,ctrly=x+tx*w*0.32,y+ty*w*0.32
            ss=sv(x,y); op=0.14+0.55*ss; wid=0.55+0.5*ss
            out+=f'<path d="M{ax:.1f},{ay:.1f} Q{ctrlx:.1f},{ctrly:.1f} {bx:.1f},{by:.1f}" fill="none" stroke="{DARK}" stroke-width="{wid:.2f}" opacity="{op:.2f}" stroke-linecap="round"/>'
            # thin highlight on the lit edge of the tube
            hlx,hly=x+nx*w*0.34,y+ny*w*0.34
            if ss<0.5:
                out+=f'<circle cx="{hlx:.1f}" cy="{hly:.1f}" r="0.5" fill="{LIGHT}" opacity="0.10"/>'
            s+=3.4
    return out
shade=head_contour()+arm_contour()
cross=""
light=""

# suckers integrated (underside rings, faded to tip)
suck=""
jr=random.Random(11)
for cpts,no,bw in arm_data:
    n=len(cpts);cum=[0]
    for i in range(1,n): cum.append(cum[-1]+math.dist(cpts[i],cpts[i-1]))
    total=cum[-1]
    def at(s):
        for i in range(1,n):
            if cum[i]>=s:
                f=(s-cum[i-1])/((cum[i]-cum[i-1])or 1)
                return (cpts[i-1][0]+(cpts[i][0]-cpts[i-1][0])*f, cpts[i-1][1]+(cpts[i][1]-cpts[i-1][1])*f, no[i])
        return (cpts[-1][0],cpts[-1][1],no[-1])
    s=total*0.05;row=0
    while s<total*0.9:
        t=s/total;w=TIP+(bw-TIP)*(1-t)**1.05
        x,y,(nx,ny,tx,ty)=at(s)
        off=(1 if row%2 else -1)*w*0.13;r=max(0.8,w*0.17)*(0.85+jr.random()*0.3)
        cx,cy=x+nx*off,y+ny*off;ang=math.degrees(math.atan2(ty,tx));op=0.42*(1-0.5*t)
        suck+=f'<g transform="rotate({ang:.0f} {cx:.1f} {cy:.1f})"><ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{r:.1f}" ry="{r*0.72:.1f}" fill="#0a2418" stroke="#cdbf93" stroke-width="0.7" opacity="{op:.2f}"/></g>'
        s+=max(4.6,w*0.62);row+=1

# skin — embossed papillae field (Octopus vulgaris): each bump lit top / shadow below
SHX,SHY=-0.3,0.32   # light from upper-left
skin="";jr2=random.Random(41);step=8.4;yy=100
while yy<548:
    xx=180
    while xx<360:
        px=xx+jr2.uniform(-3.2,3.2); py=yy+jr2.uniform(-3.2,3.2)
        xx+=step
        if jr2.random()<0.22 or not union.contains(Point(px,py)): continue
        s=sv(px,py)
        onhead = py<252 and abs(px-260)<80
        b=(1.5+jr2.random()*1.8) if onhead else (0.85+jr2.random()*0.95)
        vis=max(0.25,1-abs(s-0.45)*1.7)          # peak at mid-tone, fade in deep shade/highlight
        dop=0.3*vis; lop=0.14*vis*(0.6 if s<0.3 else 1)   # damp sparkle on the lit side
        skin+=(f'<ellipse cx="{px-SHX*b:.1f}" cy="{py+SHY*b+b*0.32:.1f}" rx="{b:.1f}" ry="{b*0.62:.1f}" fill="#03120c" opacity="{dop:.2f}"/>'
               f'<circle cx="{px+SHX*b:.1f}" cy="{py-SHY*b:.1f}" r="{b*0.44:.1f}" fill="#4fb98c" opacity="{lop:.2f}"/>')
        if onhead and b>2.5:
            skin+=f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{b*0.95:.1f}" fill="none" stroke="#03120c" stroke-width="0.5" opacity="{0.1*vis:.2f}"/>'
    yy+=step
mott=skin
# papillae — raised warty bumps (diamond on mantle + supraocular horns)
def pap(cx,cy,r):
    return (f'<ellipse cx="{cx}" cy="{cy+r*0.35:.1f}" rx="{r}" ry="{r*0.6:.1f}" fill="#03150d" opacity="0.4"/>'
            f'<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{r*0.92:.1f}" fill="#1d7a5b"/>'
            f'<ellipse cx="{cx-r*0.3:.1f}" cy="{cy-r*0.3:.1f}" rx="{r*0.5:.1f}" ry="{r*0.4:.1f}" fill="#3fae86" opacity="0.55"/>')
papillae=(pap(260,120,6)+pap(235,147,5)+pap(285,147,5)+pap(260,176,5.5)
          +pap(209,209,4)+pap(223,204,3.4)+pap(311,209,4)+pap(297,204,3.4))

import argparse
_ap=argparse.ArgumentParser(description="Atlas octopus mascot generator (v16 base)")
_ap.add_argument("--mode",default="portrait",choices=["portrait","companion"])
_ap.add_argument("--size",type=int,default=900,help="output width in px")
_ap.add_argument("--out",default="octopus-portrait.svg")
_ap.add_argument("--preview",action="store_true",help="include navy ground + latin label (QA only)")
_args=_ap.parse_args()

# companion mode: ghost the body + add one long sweeping tentacle (filled, NOT line-art)
_sweep=""; _bodyop=1.0; VBX,VBY,VBW,VBH=0,0,W,H
if _args.mode=="companion":
    _bodyop=0.5; VBX,VBY,VBW,VBH=-170,-150,720,770
    def _tent(x,y,ang,length,curl,grow,steps=82):
        pts=[(x,y)];a=math.radians(ang);ds=length/steps
        for i in range(steps):
            tt=i/steps; a+=math.radians(curl*(0.32+grow*tt*tt))
            x+=ds*math.cos(a); y+=ds*math.sin(a); pts.append((x,y))
        return pts
    _sp=_tent(205,178,212,370,1.0,3.0); _sn=norms(_sp); _n=len(_sp)
    _L=[];_R=[]
    for i in range(_n):
        t=i/(_n-1); w=(2.0+(24-2.0)*(1-t)**0.9)/2; nx,ny,_tx,_ty=_sn[i]
        _L.append((_sp[i][0]+nx*w,_sp[i][1]+ny*w)); _R.append((_sp[i][0]-nx*w,_sp[i][1]-ny*w))
    _poly=_L+_R[::-1]
    _swd="M"+"".join((("L" if i else "")+f"{x:.1f},{y:.1f}") for i,(x,y) in enumerate(_poly))+"Z"
    _cum=[0]
    for i in range(1,_n): _cum.append(_cum[-1]+math.dist(_sp[i],_sp[i-1]))
    _tot=_cum[-1]; _su=""; _s=_tot*0.05; _row=0
    def _at(s):
        for i in range(1,_n):
            if _cum[i]>=s:
                f=(s-_cum[i-1])/((_cum[i]-_cum[i-1])or 1)
                return (_sp[i-1][0]+(_sp[i][0]-_sp[i-1][0])*f,_sp[i-1][1]+(_sp[i][1]-_sp[i-1][1])*f,_sn[i])
        return (_sp[-1][0],_sp[-1][1],_sn[-1])
    while _s<_tot*0.92:
        t=_s/_tot; w=2.0+(24-2.0)*(1-t)**0.9
        x,y,(nx,ny,tx,ty)=_at(_s)
        off=w*0.15; r=max(0.7,w*0.18); cxs,cys=x+nx*off,y+ny*off; an=math.degrees(math.atan2(ty,tx))
        _su+=f'<g transform="rotate({an:.0f} {cxs:.1f} {cys:.1f})"><ellipse cx="{cxs:.1f}" cy="{cys:.1f}" rx="{r:.1f}" ry="{r*0.72:.1f}" fill="#0a2418" stroke="#cdbf93" stroke-width="0.7" opacity="0.55"/></g>'
        _s+=max(4.6,w*0.62); _row+=1
    _sweep=f'<path d="{_swd}" fill="#0b3326"/><path d="{_swd}" fill="url(#mg)" transform="translate(-0.6,-0.7)"/>{_su}'
_vb=f"{VBX} {VBY} {VBW} {VBH}"
_w=_args.size; _h=int(round(_w*VBH/VBW))
_bg=f'<rect x="{VBX}" y="{VBY}" width="{VBW}" height="{VBH}" fill="#070d17"/>' if _args.preview else ''
_label=('<line x1="200" y1="556" x2="320" y2="556" stroke="#e7ddbe" stroke-width="0.8" opacity="0.4"/>'
        '<text x="260" y="574" text-anchor="middle" font-size="13" font-style="italic"'
        ' fill="rgba(231,221,190,0.78)">Octopoda cartographica</text>') if _args.preview else ''

svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{_w}" height="{_h}" viewBox="{_vb}" font-family="Georgia,serif" role="img"><title>Atlas octopus mascot</title>
<defs><clipPath id="body"><path d="{UNION_D}"/></clipPath>
<radialGradient id="mg" gradientUnits="userSpaceOnUse" cx="230" cy="164" r="250">
<stop offset="0" stop-color="#207f5e"/><stop offset="0.55" stop-color="#0f4836"/><stop offset="1" stop-color="#061f15"/></radialGradient></defs>
{_bg}
<g opacity="{_bodyop}">
<path d="{UNION_D}" fill="url(#mg)"/>
<g clip-path="url(#body)">{shade}{cross}{light}{mott}{suck}{papillae}</g>
<path d="{UNION_D}" fill="none" stroke="#cfc6a0" stroke-width="1.0" opacity="0.45"/>
<g>
<!-- deep ancestral sockets -->
<ellipse cx="221" cy="227" rx="15" ry="11.5" fill="#04150d" opacity="0.7"/>
<ellipse cx="299" cy="227" rx="15" ry="11.5" fill="#04150d" opacity="0.7"/>
<g transform="translate(221,228) rotate(-10)"><ellipse rx="9.6" ry="7" fill="#070f0a"/><ellipse rx="8.2" ry="5.6" fill="#a89a64"/><ellipse rx="8.2" ry="5.6" fill="#06120c" opacity="0.25" transform="translate(0,1.6)"/><rect x="-7" y="-1" width="14" height="2" rx="1" fill="#05100a"/><circle cx="-2.4" cy="-2.2" r="1.1" fill="#9ff3cd"/></g>
<g transform="translate(299,228) rotate(10)"><ellipse rx="9.6" ry="7" fill="#070f0a"/><ellipse rx="8.2" ry="5.6" fill="#a89a64"/><ellipse rx="8.2" ry="5.6" fill="#06120c" opacity="0.25" transform="translate(0,1.6)"/><rect x="-7" y="-1" width="14" height="2" rx="1" fill="#05100a"/><circle cx="2.4" cy="-2.2" r="1.1" fill="#9ff3cd"/></g>
<!-- hooded lids -->
<path d="M209,221 Q221,214 234,220" fill="none" stroke="#04150d" stroke-width="3.4" stroke-linecap="round" opacity="0.65"/>
<path d="M286,220 Q299,214 311,221" fill="none" stroke="#04150d" stroke-width="3.4" stroke-linecap="round" opacity="0.65"/>
</g>
</g>
{_sweep}
{_label}
</svg>'''
open(_args.out,"w").write(svg)
print(f"[{_args.mode}] wrote {_args.out}  {_w}x{_h}  bytes={len(svg)}  verts={len(ext)}")
