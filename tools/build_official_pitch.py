"""Fill the user-supplied AI Builder Cup template; preserve mandatory section order."""
import argparse,hashlib,json
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--template',type=Path,required=True);p.add_argument('--out',type=Path,default=Path('/tmp/lingolive-submission-current/deck/LingoLive-Pitch-Deck.pptx'));p.add_argument('--public-repo',action='store_true');a=p.parse_args();r=Presentation(a.template)
assert len(r.slides)==16
# Remove only the template download-instructions page and the empty spare page.
for i in [14,1]:
 sid=r.slides._sldIdLst[i];r.part.drop_rel(sid.rId);r.slides._sldIdLst.remove(sid)
slides=list(r.slides);created=[]
BLUE='1A73E8';GREEN='188038';INK='202124';GRAY='5F6368';LIGHT='F1F6FD'
BASE='https://storage.googleapis.com/lingolive-demo-358650584819/ai-builder-cup-2026/submission-2026-10-18/'
def text(s,x,y,w,h,content,size=15,color=INK,bold=False,fill=None,align=None):
 sh=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=sh.text_frame;tf.clear();tf.word_wrap=True;tf.margin_left=Inches(.06);tf.margin_right=Inches(.06);tf.margin_top=Inches(.03);tf.margin_bottom=0
 for i,line in enumerate(content.split('\n')):
  para=tf.paragraphs[0] if i==0 else tf.add_paragraph();para.text=line;para.font.name='Arial';para.font.size=Pt(size);para.font.bold=bold;para.font.color.rgb=RGBColor.from_string(color);para.space_after=Pt(7)
  if align is not None:para.alignment=align
 if fill:sh.fill.solid();sh.fill.fore_color.rgb=RGBColor.from_string(fill);sh.line.fill.background()
 created.append((s,sh));return sh

def card(s,x,y,w,h,title,body):
 box=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h));box.fill.solid();box.fill.fore_color.rgb=RGBColor.from_string(LIGHT);box.line.color.rgb=RGBColor.from_string('DADCE0')
 if h<1:
  text(s,x+.13,y+.03,w-.26,.25,title,13,BLUE,True);text(s,x+.13,y+.29,w-.26,h-.31,body,11)
 else:
  text(s,x+.13,y+.10,w-.26,.36,title,15,BLUE,True);text(s,x+.13,y+.53,w-.26,h-.57,body,13)

def title(s,value):
 sh=next(sh for sh in s.shapes if sh.has_text_frame and sh.text.strip());sh.text=value;sh.height=Inches(.62)
 for q in sh.text_frame.paragraphs:q.font.name='Arial';q.font.size=Pt(18);q.font.bold=True;q.font.color.rgb=RGBColor.from_string(INK)

def link(s,y,label,url):
 sh=text(s,.55,y,8.8,.50,label,15,BLUE);sh.text_frame.paragraphs[0].runs[0].hyperlink.address=url

cover=slides[0].shapes[0];cover.text='Team Details\nProject: LingoLive — Understand. Reply. Keep going.\nTeam name: CreativeEngine\nTeam leader: Ashish T. Vasant | Member: Janhvi Singh\nProblem: Help migrants participate in everyday conversations in an unfamiliar language.\nTheme: Sustainability & Social Impact | Category: Accessibility'
for i,q in enumerate(cover.text_frame.paragraphs):q.font.name='Arial';q.font.size=Pt(18 if i==0 else 13);q.font.bold=i==0;q.space_after=Pt(5)

s=slides[1];title(s,'Brief about the idea');text(s,.5,1.48,8.9,.65,'A conversation assistant for life in a new place.',25,INK,True);text(s,.5,2.20,8.9,1.05,'LingoLive listens to another person, explains their words and offers three useful replies in the local language, with pronunciation. Plans, recent turns and location-linked memory make those replies personal.',17)
for x,t,b in [(0.55,'Understand now','Live speech → familiar-language meaning'),(3.65,'Reply confidently','Relevant options + pronunciation'),(6.75,'Learn afterwards','Saved exchanges → personal practice')]:card(s,x,3.55,2.75,1.30,t,b)

s=slides[2];title(s,'Opportunities');card(s,.5,1.50,9,1.05,'The problem: understanding is only half the conversation','A newcomer must also decide what to say, pronounce it and complete a task while the other person waits.');card(s,.5,2.72,9,1.05,'The solution: replies that fit the person and the moment','Combines the current turn, a pre-task plan, activities, preferences and nearby saved-place notes. Learner readbacks update context.');card(s,.5,3.94,9,1.10,'Users and customers across regions','Interstate and international migrants. Customers: migrant associations, NGOs, universities, employers and relocation teams anywhere.')

s=slides[3];title(s,'List of features offered by the solution')
features=[('Hear and respond','Live multilingual speech; three contextual replies.'),('Say it your way','Express familiar-language intent in the local language.'),('Recognize learner readbacks','Forgiving repeat matching + session voice estimates.'),('Plan before leaving','Cab → optional tea → station; Done / Skip / Previous.'),('Location-linked memory','Opt-in place facts recalled on a fresh return nearby.'),('Personal memory','Editable activities and preferences; relevant retrieval.'),('Learn afterwards','Saved exchanges; word bubbles and pronunciation.'),('Simple, guarded access','One large microphone control; Google sign-in; quotas.')]
for i,(t,b) in enumerate(features):card(s,.5+(i%2)*4.6,1.5+(i//2)*.90,4.4,.79,t,b)

s=slides[4];title(s,'Process flow diagram or Use-case diagram')
for x,t,b in [(0.5,'1. Plan + listen','Optional goal; one large microphone button'),(3.7,'2. Understand','Live Transcribe produces committed speech'),(6.9,'3. Route the turn','Readback matching + recent voice clues')]:card(s,x,1.55,2.6,1.30,t,b)
text(s,3.15,1.88,.45,.5,'→',23,BLUE,True);text(s,6.35,1.88,.45,.5,'→',23,BLUE,True)
card(s,.5,3.2,4.35,1.45,'Learner repeats a suggested reply','Keep the actual spoken words in context and preserve the options. Continue listening for the other person.');card(s,5.15,3.2,4.35,1.45,'A new turn needs assistance','Parallel Flash-Lite tasks → meaning + three replies → learner speaks → Saved review afterwards.');text(s,.55,4.86,8.9,.30,'The learner can correct who spoke. Goals, plan progress and relevant place memories follow the conversation.',11,GRAY)

# Optional section intentionally reserved, as requested; preserve the template heading.
s=slides[5];title(s,'Wireframes/Mock diagrams of the proposed solution (optional)')

s=slides[6];title(s,'Architecture diagram of the proposed solution')
s.shapes.add_picture(str(ROOT/'docs/submission/architecture.png'),Inches(.5),Inches(1.40),width=Inches(9))

s=slides[7];title(s,'Technologies to be used in the solution')
for i,(t,b) in enumerate([('Live speech','Gemini 3.5 Transcribe Live streams multilingual audio while the person speaks.'),('Fast, economical replies','Two concurrent Gemini 3.1 Flash-Lite tasks: source understanding and reply generation; compact JSON.'),('Google Cloud','Cloud Run + Vertex AI; Firebase Google sign-in; private Cloud Storage quotas; Secret Manager.'),('Local personalization','IndexedDB lessons; editable learner profiles, task plans and guarded location-linked memory.')]):card(s,.5,1.55+i*.86,9,.76,t,b)

s=slides[8];title(s,'Estimated implementation cost (optional)')
card(s,.5,1.50,4.35,1.15,'~US$5 / learner / month · ₹450','200 listening minutes + 400 new reply turns per month.')
card(s,5.15,1.50,4.35,1.15,'100 learners · ~US$465 / month','Shared community estimate, including contingency.')
text(s,.55,2.85,8.9,.57,'Per learner: speech $1.79 + generation $1.76 + shared infrastructure $0.30. Add 20% contingency, then round the budget to US$5.',15)
text(s,.55,3.60,8.9,.73,'Usage estimate: 10 minutes and 20 new reply turns per day, on 20 days per month; hosting shared across 100 active learners. Each turn uses two parallel calls.',14)
text(s,.55,4.47,8.9,.66,'Rate basis: Live Transcribe $0.008925/min; Flash-Lite $0.25/M input and $1.50/M output. Standard global rates checked 18 Oct 2026; before tax and credits. INR planning rate: ₹90/US$. Detailed assumptions: technical PDF.',11,GRAY)

s=slides[9];title(s,'Snapshots of the prototype')
shots=ROOT/'validation';names=[('web-plans-cloud.png','Plan before leaving'),('web-express-cloud.png','Find a useful reply'),('web-replies-review.png','Learn afterwards')]
from PIL import Image
for i,(name,label) in enumerate(names):
 file=shots/name;im=Image.open(file);im=im.crop((0,0,im.width,min(im.height,round(im.width*1.95))))
 tmp=a.out.parent/(name+'.crop.png');tmp.parent.mkdir(parents=True,exist_ok=True);im.save(tmp)
 s.shapes.add_picture(str(tmp),Inches(1.15+i*3.15),Inches(1.55),height=Inches(3.1));text(s,.5+i*3.15,4.66,2.8,.34,label,13,BLUE,True,align=PP_ALIGN.CENTER)
text(s,.55,5.05,8.9,.25,'Recorded prototype UI; Saved view uses sample lesson data. The demonstration includes real Google AI responses.',10,GRAY)

s=slides[10];title(s,'Prototype Performance report/Benchmarking');text(s,.55,1.5,8.8,.52,'Designed for an approximately two-second warm lesson.',22,INK,True)
rows=[('1.79 s mean · 10 lessons','Recorded v1.5 warm hosted run; all complete responses succeeded.'),('2.065 s mean · 4 cases','Later v1.9 Kannada task flows: cab, tea, café and station.'),('Parallel critical path','Source understanding and replies run together; compact output and warm HTTP.'),('Local reuse','Readbacks preserve replies; word taps and saved review reuse lesson data.'),('Memory and access checks','134 backend tests; 16 place-core checks and 8 place browser flows.')]
for i,(t,b) in enumerate(rows):text(s,.55,2.2+i*.51,3.0,.46,t,13,BLUE,True);text(s,3.62,2.2+i*.51,5.85,.46,b,12)
text(s,.55,4.98,8.9,.30,'Timings measure warm lesson requests; speech also includes transcription finalization and device/network time.',11,GRAY)

s=slides[11];title(s,'Additional Details/Future Development (if any)');card(s,.5,1.55,4.35,2.95,'Adoption and business estimates','20 partners × 100 learners = 2,000 learners.\nCommunity-sponsored usage packages.\nEstimated operating budget: ~US$5 / active learner / month in a 100-member community.\nPartners: migrant groups, NGOs, campuses and employers globally.');card(s,5.15,1.55,4.35,2.95,'Pilot targets and next delivery','Four weeks, 50 learners: ~1,600 encounters and 8,000 assisted turns.\nTargets: 70% useful reply sets; 80% task completion.\nNext: more language pairs, partner allowances and opt-in local voice enrollment.');text(s,.55,4.82,8.9,.42,'Adoption, pilot outcomes and unit economics are planning estimates/targets; assumptions and scale scenario are in the technical PDF.',11,GRAY)

s=slides[12];title(s,'Provide links to your:')
link(s,1.6,'GitHub source — github.com/U4AR/LingoLive','https://github.com/U4AR/LingoLive')
link(s,2.35,'Demo video — 3:17 working demonstration',BASE+'LingoLive-Demo.mp4')
link(s,3.1,'Final product — live Google Cloud Run prototype','https://lingolive-358650584819.us-central1.run.app')
link(s,3.85,'Submission materials — pitch, technical PDF and entry text',BASE+'index.html')
text(s,.55,4.6,8.9,.6,'Sign in with any verified Google account. A personal Google model key is optional.\nShared daily demo allowance: 20 listening minutes and 100 two-branch lessons; midnight IST reset.',11,GRAY)

# Closing branding is unmodified. Add restrained pagination to content slides.
for i,s in enumerate(slides[1:-1],2):text(s,8.95,5.26,.5,.2,str(i),8,GRAY,align=PP_ALIGN.RIGHT)
for s,sh in created:assert sh.left>=0 and sh.top>=0 and sh.left+sh.width<=r.slide_width+5 and sh.top+sh.height<=r.slide_height+5
assert len(slides)==14;a.out.parent.mkdir(parents=True,exist_ok=True);r.save(a.out)
report={'source_template_sha256':hashlib.sha256(a.template.read_bytes()).hexdigest(),'source_slides':16,'output_slides':14,'removed_pages':['download instruction page','empty spare page'],'required_sections_preserved_in_order':True,'branding_preserved':True,'theme':'Sustainability & Social Impact','category':'Accessibility','wireframe_body_empty':True,'architecture_diagram':'docs/submission/architecture.svg','cost_assumptions':'docs/submission/COST-ESTIMATE.json','team':'CreativeEngine','team_members':['Ashish T. Vasant','Janhvi Singh'],'repo_public_at_render':a.public_repo,'file':a.out.name,'bytes':a.out.stat().st_size}
(a.out.parent/'pitch-template-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
