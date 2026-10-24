"""Versioned deterministic contracts shared by authoring, training and tests.

No clothing/name feature enters the policy. All scene characters and farm jobs
are fictional design choices, not observations about Pandori residents.
"""
import math
import unicodedata

SCHEMA='v25.state64.v1'
FEATURE_GROUPS=[
 ['hour_fraction','daylight','raining','wetness','wind_strength','cold','season_progress','is_weekend'],
 ['fatigue','hunger','thirst','social_need','health','carrying','waiting','interrupted'],
 ['work_window','task_progress','has_task','can_interrupt','cooldown','commitment','shop_shift','return_window'],
 ['shelter_available','work_available','seat_available','conversation_available','passage_blocked','tool_available','shop_open','target_available'],
 ['at_work','at_home','at_shelter','distance_to_work','path_blocked','distance_to_home','vehicle_near','path_valid'],
 ['familiarity','last_greeting','last_conversation','last_help','recent_rain','recent_yield','task_success','task_failure'],
 ['job_assigned','soil_wetness','crop_stage','irrigation_due','supplies_available','reservation_owned','vehicle_available','plot_accessible'],
 ['can_inspect','can_stock','can_drive','can_commute','can_carry','can_visit','talkativeness','rest_preference']]
FEATURES=sum(FEATURE_GROUPS,[])
ACTIONS=['idle','travel_to_task','perform_task','rest','seek_shelter','greet','return_home','yield_passage','replan']+['reserved_%02d'%i for i in range(9,48)]

def sanitize(values):
    if len(values)!=64:raise ValueError('Expected exactly 64 features')
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in values):raise ValueError('Non-finite feature')
    return [min(1.,max(0.,float(v))) for v in values]

def valid_actions(x):
    x=sanitize(x);m=[False]*48
    m[0]=True;m[8]=True
    m[1]=bool(x[16]>.5 and x[48]>.5 and x[25]>.5 and x[31]>.5 and x[39]>.5 and x[32]<.5)
    m[2]=bool(x[16]>.5 and x[48]>.5 and x[25]>.5 and x[32]>.5 and x[53]>.5)
    m[3]=bool(x[26]>.5 and x[5]<.5)
    m[4]=bool(x[24]>.5 and x[19]>.5)
    m[5]=bool(x[27]>.5 and x[20]<.5 and x[5]<.5)
    m[6]=bool(x[33]<.5 and x[39]>.5)
    m[7]=bool(x[28]>.5 or x[36]>.5 or x[38]>.5)
    if x[28]>.5 or x[36]>.5:
        for a in (1,2,6):m[a]=False
    if x[2]>.5:m[1]=m[2]=False
    return m

def baseline(x,mask=None):
    m=valid_actions(x) if mask is None else mask
    order=([7] if x[28]>.5 or x[36]>.5 else [])+([4] if x[2]>.5 else [])
    order+=([6,0] if x[16]<.5 else [])+([3] if x[8]>.8 else [])+[2,1,0,8]
    return next((a for a in order if m[a]),0)

def select_action(logits,mask,fallback):
    if len(mask)!=48 or not any(mask):return 0
    if logits is None or len(logits)!=48 or not all(math.isfinite(v) for v in logits):return fallback if mask[fallback] else 0
    ranked=sorted((i for i in range(48) if mask[i]),key=lambda i:logits[i],reverse=True)
    if len(ranked)>1 and logits[ranked[0]]-logits[ranked[1]]<.5:return fallback if mask[fallback] else 0
    return ranked[0]

def normalize_text(text):
    text=unicodedata.normalize('NFC',text).strip()
    if len(text.encode('utf-8'))>256:raise ValueError('Please use a question of at most 256 UTF-8 bytes.')
    return text

class Reservations:
    def __init__(self):self.owners={}
    def acquire(self,slot,owner):
        if slot in self.owners and self.owners[slot]!=owner:return False
        self.owners[slot]=owner;return True
    def release(self,owner):self.owners={s:o for s,o in self.owners.items() if o!=owner}
