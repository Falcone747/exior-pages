import asyncio, importlib.util, os
from pathlib import Path
from browser_use import Agent, BrowserProfile, ChatOllama

BASE='/opt/exior-contact-indexer/sender-v6-browseruse-fixed.py'
spec=importlib.util.spec_from_file_location('v6base', BASE)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

CHROMIUM_EXECUTABLE=os.environ['CHROMIUM_EXECUTABLE']

async def run_agent(url):
    llm=ChatOllama(model=m.MODEL)
    profile=BrowserProfile(
        executable_path=CHROMIUM_EXECUTABLE,
        headless=True,
        enable_default_extensions=False,
        user_data_dir=None,
        cross_origin_iframes=True,
        args=['--no-sandbox','--disable-dev-shm-usage','--no-zygote'],
    )
    task=f'''Open exactly this company contact page: {url}\n\nGoal: send ONE legitimate B2B enquiry from EXIOR to this marketing agency.\n\nUse these truthful values where fields request them:\nName: {m.NAME}\nCompany: {m.COMPANY}\nEmail: {m.EMAIL}\nPhone: {m.PHONE}\nWebsite: {m.WEBSITE}\nMessage:\n{m.MESSAGE}\n\nRules:\n- Understand the rendered page and actual form, including unusual labels, multi-step forms, selects and embedded frames.\n- Choose neutral business/general/new-project options when a required dropdown asks for enquiry type.\n- Never invent personal or company facts beyond the values above.\n- Never bypass CAPTCHA, anti-bot protections, login, or access controls.\n- If the page explicitly says no sales, no vendors, no solicitation, or the form is only for support/jobs/press, STOP without submitting.\n- Submit AT MOST ONCE. After clicking final submit once, do not retry.\n- Return exactly one prefix: SUCCESS_CONFIRMED, SUBMIT_ATTEMPTED, or NOT_SUBMITTED, then a concise reason.\n'''
    agent=Agent(task=task,llm=llm,browser_profile=profile,max_actions_per_step=5,max_failures=2)
    hist=await asyncio.wait_for(agent.run(max_steps=18),timeout=180)
    try: return hist.final_result() or ''
    except Exception: return str(hist)

m.run_agent=run_agent

if __name__=='__main__':
    asyncio.run(m.main())
