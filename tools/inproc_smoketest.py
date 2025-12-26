#!/usr/bin/env python3
"""Run smoke test against the FastAPI app in-process using TestClient.

This avoids needing a running uvicorn server and exercises the endpoints.
"""
from dotenv import load_dotenv
load_dotenv()
import os
from fastapi.testclient import TestClient

from task_scheduler.api import app

client = TestClient(app)

def run():
    print('Running in-process smoke test')
    # Register admin (ignore if exists)
    reg = client.post('/api/auth/register', json={'username':'auto_admin','password':'AdminPass123!','role':'admin'})
    print('register status', reg.status_code, reg.json() if reg.status_code<400 else reg.text)
    login = client.post('/api/auth/login', data={'username':'auto_admin','password':'AdminPass123!'})
    print('login status', login.status_code)
    if login.status_code!=200:
        print('Login failed, aborting')
        return
    token = login.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}'}

    # Create members
    for m in [{'name':'Alice','id':'alice','office_days':[0,1,2,3,4]},{'name':'Bob','id':'bob','office_days':[0,1,2,3,4]}]:
        r = client.post('/api/team-members', json=m, headers=headers)
        print('create member', m['id'], r.status_code, r.json() if r.status_code<400 else r.text)

    # Generate schedule
    from datetime import date, timedelta
    start = (date.today()+timedelta(days=1)).isoformat()
    end = (date.today()+timedelta(days=7)).isoformat()
    gen = client.post('/api/schedules/generate', json={'start_date':start,'end_date':end,'fairness_aggressiveness':1}, headers=headers)
    print('generate', gen.status_code)
    if gen.status_code==200:
        print(gen.json())
        sid = gen.json().get('schedule_id')
        if sid:
            details = client.get(f'/api/schedules/{sid}', headers=headers)
            print('schedule details', details.status_code)
            if details.status_code==200:
                print(details.json())

if __name__=='__main__':
    run()
