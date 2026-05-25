"""
robot_ui.py - AI Exhibition Robot Face UI [v4 FIXED]
=====================================================
- UI ALWAYS updates on any detection callback
- Greeting text + robot expression change immediately
- TTS only on is_new_visitor=True
- No 8-digit hex colors (Tkinter compatible)
"""

import customtkinter as ctk
import tkinter as tk
import math, time, random, datetime
from typing import Optional
from detector import GenderDetector, DetectionResult
from greeting import Greeter


PALETTES = {
    "none":         {"bg":"#050A14","accent":"#00BFFF","text":"#FFFFFF","panel":"#0D1B2A"},
    "male":         {"bg":"#020C1B","accent":"#4FC3F7","text":"#E3F2FD","panel":"#0A1929"},
    "female":       {"bg":"#1A0010","accent":"#F48FB1","text":"#FCE4EC","panel":"#2D0020"},
    "group_male":   {"bg":"#010D1A","accent":"#29B6F6","text":"#E1F5FE","panel":"#071520"},
    "group_female": {"bg":"#1C0018","accent":"#EC407A","text":"#FCE4EC","panel":"#2A0025"},
    "group_mixed":  {"bg":"#0D0020","accent":"#AB47BC","text":"#F3E5F5","panel":"#1A0030"},
}

def dim(color:str, f:float)->str:
    c=color.lstrip("#")
    r=max(0,min(255,int(int(c[0:2],16)*f)))
    g=max(0,min(255,int(int(c[2:4],16)*f)))
    b=max(0,min(255,int(int(c[4:6],16)*f)))
    return f"#{r:02X}{g:02X}{b:02X}"


# ═══════════════════════════════════
#  Robot Canvas
# ═══════════════════════════════════
class RobotCanvas(tk.Canvas):

    def __init__(self, master, width=430, height=430, **kw):
        super().__init__(master, width=width, height=height,
                         bg="#050A14", highlightthickness=0, **kw)
        self.W = width
        self.H = height
        self._scenario    = "none"
        self._accent      = "#00BFFF"
        self._blink_open  = True
        self._mouth_state = "neutral"
        self._phase       = 0.0
        self._eye_dy      = 0
        self._scan_y      = 0
        self._particles   = []
        self._running     = True
        self._flash       = 0
        self._init_particles()
        self._tick()

    def set_scenario(self, scenario:str, accent:str, flash:bool=False):
        self._scenario    = scenario
        self._accent      = accent
        self._mouth_state = ("neutral" if scenario=="none"
                             else "smile" if scenario in ("male","female")
                             else "open")
        if flash and scenario != "none":
            self._flash = 10

    def _init_particles(self):
        for _ in range(22):
            self._particles.append({
                "x": random.randint(0,self.W),
                "y": random.randint(0,self.H),
                "r": random.uniform(1.4,3.5),
                "dx":random.uniform(-0.4,0.4),
                "dy":random.uniform(-0.7,-0.15),
            })

    def _tick(self):
        if not self._running: return
        t = time.time()
        self._phase      = t
        self._blink_open = (int(t*4)%14 != 0)
        self._eye_dy     = int(math.sin(t*1.2)*3)
        self._scan_y     = int((t*55)%self.H)
        if self._flash > 0: self._flash -= 1
        for p in self._particles:
            p["x"]+=p["dx"]; p["y"]+=p["dy"]
            if p["y"]<-5: p["y"]=self.H+5; p["x"]=random.randint(0,self.W)
        self._draw()
        self.after(45, self._tick)

    # ── Drawing ──────────────────────────────
    def _draw(self):
        self.delete("all")
        acc = self._accent
        bg  = PALETTES.get(self._scenario, PALETTES["none"])["bg"]
        self.configure(bg=bg)
        self._bg(acc)
        self._head(acc)
        self._ears(acc)
        self._antennae(acc)
        self._eyes(acc)
        self._nose(acc)
        self._mouth(acc)
        if self._flash > 0:
            self._draw_flash(acc)

    def _bg(self, acc):
        d1=dim(acc,0.06); d2=dim(acc,0.12)
        for i in range(0,self.H,8):
            self.create_line(0,i,self.W,i,fill=d2 if i%16==0 else d1,width=1)
        self.create_line(0,self._scan_y,self.W,self._scan_y,
                         fill=acc,width=1,stipple="gray25")
        for p in self._particles:
            x,y,r=p["x"],p["y"],p["r"]
            self.create_oval(x-r,y-r,x+r,y+r,fill=acc,outline="")

    def _rrect(self,x1,y1,x2,y2,r,**kw):
        pts=[x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,
             x2,y2-r,x2,y2,x2-r,y2,x1+r,y2,
             x1,y2,x1,y2-r,x1,y1+r,x1,y1,x1+r,y1]
        self.create_polygon(pts,smooth=True,**kw)

    def _head(self, acc):
        cx,cy=self.W//2,self.H//2
        for i in range(5,0,-1):
            self.create_oval(cx-130-i*5,cy-110-i*5,
                             cx+130+i*5,cy+130+i*5,
                             outline=dim(acc,i*0.14),width=1)
        x1,y1,x2,y2=cx-130,cy-110,cx+130,cy+130
        self._rrect(x1,y1,x2,y2,30,fill="#0D1B2A",outline=acc,width=2)
        self.create_rectangle(x1+8,y1+8,x2-8,y1+36,fill=dim(acc,0.20),outline="")
        self.create_text(cx,y1+22,text="  A . I .  EXHIBITION  ",
                         font=("Courier New",10,"bold"),fill=acc)

    def _antennae(self, acc):
        cx=self.W//2; top=self.H//2-110
        self.create_line(cx-50,top,cx-68,top-42,fill=acc,width=2)
        self.create_oval(cx-74,top-52,cx-60,top-38,fill=acc,outline="white",width=1)
        self.create_line(cx+50,top,cx+68,top-42,fill=acc,width=2)
        self.create_oval(cx+60,top-52,cx+74,top-38,fill=acc,outline="white",width=1)
        if int(time.time()*2)%2==0:
            self.create_oval(cx-74,top-52,cx-60,top-38,fill="white",outline="")
        else:
            self.create_oval(cx+60,top-52,cx+74,top-38,fill="white",outline="")

    def _ears(self, acc):
        cx,cy=self.W//2,self.H//2; d=dim(acc,0.38)
        for sx,ex in [(cx-130,cx-148),(cx+130,cx+148)]:
            self._rrect(min(sx,ex),cy-50,max(sx,ex),cy+40,4,fill="#0D1B2A",outline=acc,width=1)
            for i in range(3):
                yy=cy-28+i*22
                self.create_rectangle(min(sx,ex)+3,yy,max(sx,ex)-3,yy+12,fill=d,outline="")

    def _eyes(self, acc):
        cx,cy=self.W//2,self.H//2
        ey=cy-28+self._eye_dy
        for ex in [cx-55,cx+55]:
            self.create_oval(ex-30,ey-22,ex+30,ey+22,fill="#020810",outline=acc,width=2)
            if self._blink_open:
                self.create_oval(ex-19,ey-16,ex+19,ey+16,
                                 fill="#001830",outline=dim(acc,0.60),width=1)
                self.create_oval(ex-10,ey-10,ex+10,ey+10,fill="white",outline="")
                self.create_oval(ex-5,ey-5,ex+5,ey+5,fill=acc,outline="")
                self.create_oval(ex+2,ey-8,ex+6,ey-4,fill="white",outline="")
            else:
                self.create_line(ex-24,ey,ex+24,ey,fill=acc,width=3)

    def _nose(self, acc):
        cx,cy=self.W//2,self.H//2; nx,ny=cx,cy+8
        self.create_polygon(nx-9,ny+11,nx+9,ny+11,nx,ny-6,
                             fill=dim(acc,0.5),outline=acc,width=1)

    def _mouth(self, acc):
        cx,cy=self.W//2,self.H//2; my=cy+56; t=self._phase
        if self._mouth_state=="neutral":
            self.create_line(cx-35,my,cx+35,my,fill=acc,width=3,capstyle=tk.ROUND)
        elif self._mouth_state=="smile":
            amp=18+5*math.sin(t*2)
            pts=[]
            for i in range(22):
                a=math.pi*i/21
                pts.extend([cx-42+i*4, my+amp*math.sin(a)])
            self.create_line(*pts,fill=acc,width=3,smooth=True,capstyle=tk.ROUND)
            for i in range(5):
                tx=cx-18+i*9
                self.create_rectangle(tx,my+3,tx+6,my+11,fill="white",outline="")
        elif self._mouth_state=="open":
            ow=46+int(6*math.sin(t*3)); oh=22+int(4*math.sin(t*4))
            self.create_oval(cx-ow,my-oh,cx+ow,my+oh,
                             fill=dim(acc,0.28),outline=acc,width=2)
            self.create_oval(cx-16,my-2,cx+16,my+18,fill="#FF6B9D",outline="")

    def _draw_flash(self, acc):
        self.create_rectangle(0,0,self.W,self.H,outline=acc,
                               width=max(1,int(5*self._flash/10)))
        self.create_text(self.W//2,16,text="NEW VISITOR DETECTED",
                         font=("Courier New",10,"bold"),fill=acc)


# ═══════════════════════════════════
#  Main App
# ═══════════════════════════════════
class RobotExhibitionApp:

    def __init__(self, root:ctk.CTk):
        self.root    = root
        self.root.title("AI Exhibition - Smart Greeter Bot")
        self.root.geometry("1280x800")
        self.root.minsize(900,600)
        self.root.configure(fg_color="#050A14")
        try: self.root.state("zoomed")
        except: pass

        self._scenario     = "none"
        self._palette      = PALETTES["none"]
        self._tw_target    = ""
        self._tw_idx       = 0

        self._build_ui()
        self._greeter  = Greeter(cooldown=4.0)
        self._detector = GenderDetector()
        self._detector.start(callback=self._on_detection)
        self._clock_tick()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Build UI ─────────────────────────────
    def _build_ui(self):
        self.root.columnconfigure(0,weight=2)
        self.root.columnconfigure(1,weight=3)
        self.root.rowconfigure(0,weight=0)
        self.root.rowconfigure(1,weight=1)
        self.root.rowconfigure(2,weight=0)

        # Header
        self.hdr=ctk.CTkFrame(self.root,fg_color="#030A12",height=58,corner_radius=0)
        self.hdr.grid(row=0,column=0,columnspan=2,sticky="ew")
        self.hdr.grid_propagate(False)
        self.lbl_hdr=ctk.CTkLabel(self.hdr,
            text="AI EXHIBITION  —  SMART VISITOR GREETER",
            font=ctk.CTkFont("Courier New",19,"bold"),text_color="#00BFFF")
        self.lbl_hdr.place(relx=0.5,rely=0.5,anchor="center")

        # Left panel – robot
        self.lf=ctk.CTkFrame(self.root,fg_color="#050A14",corner_radius=0)
        self.lf.grid(row=1,column=0,sticky="nsew")
        self.lf.columnconfigure(0,weight=1); self.lf.rowconfigure(0,weight=1)
        self.robot=RobotCanvas(self.lf,width=430,height=430)
        self.robot.grid(row=0,column=0,padx=15,pady=15)

        # Right panel – greeting
        self.rf=ctk.CTkFrame(self.root,fg_color="#050A14",corner_radius=0)
        self.rf.grid(row=1,column=1,sticky="nsew")
        self.rf.columnconfigure(0,weight=1)
        self.rf.rowconfigure(0,weight=1)
        self.rf.rowconfigure(1,weight=0)
        self.rf.rowconfigure(2,weight=0)
        self.rf.rowconfigure(3,weight=1)

        # Card
        self.card=ctk.CTkFrame(self.rf,fg_color="#0D1B2A",
                                corner_radius=22,border_width=2,border_color="#00BFFF")
        self.card.grid(row=1,column=0,padx=28,pady=8,sticky="ew")
        self.card.columnconfigure(0,weight=1)

        self.lbl_emoji=ctk.CTkLabel(self.card,text="👀",
                                     font=ctk.CTkFont("Segoe UI Emoji",68))
        self.lbl_emoji.grid(row=0,column=0,pady=(28,4))

        self.lbl_greet=ctk.CTkLabel(self.card,text="Welcome to AI Exhibition!",
            font=ctk.CTkFont("Courier New",25,"bold"),
            text_color="#FFFFFF",wraplength=460,justify="center")
        self.lbl_greet.grid(row=1,column=0,pady=4,padx=16)

        self.lbl_sub=ctk.CTkLabel(self.card,text="Scanning for visitors...",
            font=ctk.CTkFont("Courier New",12),text_color="#00BFFF")
        self.lbl_sub.grid(row=2,column=0,pady=(4,22))

        # Stats
        self.stats=ctk.CTkFrame(self.rf,fg_color="#07101C",
                                  corner_radius=14,border_width=1,border_color="#1A3A5C")
        self.stats.grid(row=2,column=0,padx=28,pady=8,sticky="ew")
        self.stats.columnconfigure((0,1,2,3),weight=1)
        self._sv={}
        for i,(lbl,key) in enumerate([("Total Faces","total"),("Male","male"),
                                       ("Female","female"),("Confidence","conf")]):
            ctk.CTkLabel(self.stats,text=lbl,
                         font=ctk.CTkFont("Courier New",10),
                         text_color="#5A7A9A").grid(row=0,column=i,padx=8,pady=(10,2))
            v=ctk.StringVar(value="0")
            self._sv[key]=v
            ctk.CTkLabel(self.stats,textvariable=v,
                         font=ctk.CTkFont("Courier New",20,"bold"),
                         text_color="#00BFFF").grid(row=1,column=i,padx=8,pady=(2,12))

        self.lbl_badge=ctk.CTkLabel(self.rf,text="[ IDLE - WAITING FOR VISITOR ]",
            font=ctk.CTkFont("Courier New",11),text_color="#2A5070")
        self.lbl_badge.grid(row=3,column=0,pady=6)

        # Footer
        self.ftr=ctk.CTkFrame(self.root,fg_color="#020810",height=34,corner_radius=0)
        self.ftr.grid(row=2,column=0,columnspan=2,sticky="ew")
        self.ftr.grid_propagate(False)
        self.lbl_status=ctk.CTkLabel(self.ftr,text="  System Ready",
            font=ctk.CTkFont("Courier New",10),text_color="#2A5070")
        self.lbl_status.place(relx=0.0,rely=0.5,anchor="w",x=8)
        self.lbl_clock=ctk.CTkLabel(self.ftr,text="",
            font=ctk.CTkFont("Courier New",10),text_color="#2A5070")
        self.lbl_clock.place(relx=1.0,rely=0.5,anchor="e",x=-8)

    # ── Detection callback ───────────────────
    def _on_detection(self, result:DetectionResult):
        # Schedule on main thread — always
        self.root.after(0, lambda r=result: self._apply(r))

    def _apply(self, result:DetectionResult):
        s   = result.scenario
        p   = PALETTES.get(s, PALETTES["none"])
        acc = p["accent"]; bg=p["bg"]; txt=p["text"]; panel=p["panel"]

        # ── Always update robot face ──────────
        self.robot.set_scenario(s, acc, flash=result.is_new_visitor)

        # ── Always update colors ──────────────
        self.card.configure(border_color=acc, fg_color=panel)
        self.root.configure(fg_color=bg)
        self.lf.configure(fg_color=bg)
        self.rf.configure(fg_color=bg)
        self.lbl_hdr.configure(text_color=acc)

        # ── Always update greeting text ───────
        self.lbl_emoji.configure(text=result.emoji)
        self.lbl_greet.configure(text_color=txt)

        # Typewrite the greeting
        if s != self._scenario or result.is_new_visitor:
            self._typewrite(result.greeting_text)

        self._scenario = s

        # Sub text
        sub = ("Scanning for visitors..." if s=="none"
               else f"AI Vision Active  |  Confidence: {result.confidence*100:.0f}%")
        self.lbl_sub.configure(text=sub, text_color=acc)

        # Stats — always update
        self._sv["total"].set(str(result.total_faces))
        self._sv["male"].set(str(result.male_count))
        self._sv["female"].set(str(result.female_count))
        self._sv["conf"].set(f"{result.confidence*100:.0f}%")

        # Badge
        badges = {
            "none":         "[ IDLE - WAITING FOR VISITOR ]",
            "male":         "[ SINGLE MALE VISITOR ]",
            "female":       "[ SINGLE FEMALE VISITOR ]",
            "group_male":   f"[ GROUP - {result.male_count} MALES ]",
            "group_female": f"[ GROUP - {result.female_count} FEMALES ]",
            "group_mixed":  f"[ MIXED GROUP - {result.total_faces} VISITORS ]",
        }
        self.lbl_badge.configure(text=badges.get(s,""), text_color=acc)

        # Status bar
        if s == "none":
            status = "  System Ready  |  Camera Active  |  Waiting..."
        else:
            status = (f"  Active  |  Faces:{result.total_faces}"
                      f"  M:{result.male_count} F:{result.female_count}"
                      f"  |  {s.upper()}"
                      f"  |  {'NEW VISITOR!' if result.is_new_visitor else 'Tracking...'}")
        self.lbl_status.configure(text=status,
                                   text_color=acc if s!="none" else "#2A5070")

        # ── TTS: ONLY on new visitor ──────────
        if result.is_new_visitor:
            self._greeter.greet(s, result.speech_text, is_new_visitor=True)

    # ── Typewriter ───────────────────────────
    def _typewrite(self, text:str):
        self._tw_target = text
        self._tw_idx    = 0
        self._tw_step()

    def _tw_step(self):
        if self._tw_idx <= len(self._tw_target):
            cur = "|" if self._tw_idx < len(self._tw_target) else ""
            self.lbl_greet.configure(text=self._tw_target[:self._tw_idx]+cur)
            self._tw_idx += 1
            self.root.after(38, self._tw_step)

    # ── Clock ────────────────────────────────
    def _clock_tick(self):
        now = datetime.datetime.now().strftime("%I:%M:%S %p  |  %d %b %Y")
        self.lbl_clock.configure(text=f"{now}  ")
        self.root.after(1000, self._clock_tick)

    def _on_close(self):
        self._detector.stop()
        self.robot._running = False
        self.root.destroy()
