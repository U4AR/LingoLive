"""Durable shared demo allowance. GCS compare-and-swap precedes paid operations.

No transcripts, API keys, identities or coordinates are stored. Lost reservations
remain spent after a crash. Storage/auth failures fail closed; callers never fall
back to process counters. Quotas count connection time including idle/drain time.
"""
from __future__ import annotations
import asyncio,json,math,re,secrets,time
from dataclasses import dataclass
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from urllib.parse import quote
import httpx
from fastapi import HTTPException
IST=ZoneInfo('Asia/Kolkata')

def quota_day():
    now=datetime.fromtimestamp(time.time(),IST)
    end=(now+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
    return now.date().isoformat(),max(0,math.floor(end.timestamp()-now.timestamp()))

@dataclass(frozen=True)
class AudioReservation:
    day: str
    ticket: str
    seconds: int

class GCSQuota:
    def __init__(self,bucket,token_provider,client=None):
        if not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',bucket):raise ValueError('Invalid quota bucket')
        self.bucket=bucket;self.token_provider=token_provider
        self.client=client or httpx.AsyncClient(timeout=httpx.Timeout(8,connect=3),limits=httpx.Limits(max_connections=4))
    async def aclose(self):await self.client.aclose()
    def url(self,day):return 'https://storage.googleapis.com/storage/v1/b/'+self.bucket+'/o/'+quote('daily/'+day+'.json',safe='')
    async def _change(self,day,mutate):
        try:
            token=await self.token_provider();headers={'Authorization':'Bearer '+token}
            for attempt in range(6):
                r=await self.client.get(self.url(day),headers=headers,params={'alt':'media'})
                if r.status_code==404:
                    generation='0';data={'schema':1,'day':day,'model_calls':0,'audio_seconds':0,'reservations':{}}
                else:
                    r.raise_for_status();generation=r.headers.get('x-goog-generation')
                    if not generation:raise ValueError('Missing object generation')
                    data=r.json()
                    if data.get('schema')!=1 or data.get('day')!=day or not isinstance(data.get('reservations'),dict):raise ValueError('Invalid quota state')
                    for field in ('model_calls','audio_seconds'):
                        if type(data.get(field)) is not int or data[field]<0:raise ValueError('Invalid quota counter')
                value,changed=mutate(data)
                if not changed:return value
                r=await self.client.post('https://storage.googleapis.com/upload/storage/v1/b/'+self.bucket+'/o',headers=dict(headers,**{'Content-Type':'application/json'}),params={'uploadType':'media','name':'daily/'+day+'.json','ifGenerationMatch':generation},content=json.dumps(data,separators=(',',':')))
                if r.status_code==412:
                    await asyncio.sleep(.01*(attempt+1));continue
                r.raise_for_status();return value
            raise ValueError('Concurrent quota update')
        except HTTPException:raise
        except Exception:raise HTTPException(503,'The daily allowance could not be checked. AI is paused; please try later.') from None
    async def reserve_calls(self,units,limit):
        day,_=quota_day()
        def mutate(data):
            if units<=0 or data['model_calls']+units>limit:return False,False
            data['model_calls']+=units;return True,True
        return await self._change(day,mutate)
    async def reserve_audio(self,maximum,limit):
        day,boundary=quota_day();ticket=secrets.token_hex(16)
        def mutate(data):
            # Stop before the IST boundary; never fund tomorrow from today's pool.
            amount=min(maximum,limit-data['audio_seconds'],boundary)
            if amount<=10:return None,False
            data['audio_seconds']+=amount;data['reservations'][ticket]=amount
            return AudioReservation(day,ticket,amount),True
        return await self._change(day,mutate)
    async def settle_audio(self,reservation,seconds):
        def mutate(data):
            amount=data['reservations'].pop(reservation.ticket,None)
            if amount is None:return None,False # idempotent; never refund twice
            used=min(amount,max(0,math.ceil(seconds)))
            data['audio_seconds']-=amount-used;return None,True
        await self._change(reservation.day,mutate)
