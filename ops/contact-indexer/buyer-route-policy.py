#!/usr/bin/env python3
"""Commercial qualification policy for EXIOR marketing-agency outreach.
Conservative by design: scanner can discover broadly, but only buyer-state + neutral routes become sendable.
"""
import re
from urllib.parse import urlparse

BAD_ROUTE_PATTERNS=(
    r'/request[-_/]?a[-_/]?quote', r'/get[-_/]?a[-_/]?quote', r'/quote',
    r'/start[-_/]?a[-_/]?project', r'/project[-_/]?brief', r'/brief',
    r'/work[-_/]?with[-_/]?us', r'/hire[-_/]?us', r'/get[-_/]?started',
    r'/book[-_/]?a[-_/]?call', r'/discovery[-_/]?call', r'/free[-_/]?consult',
)
GOOD_ROUTE_PATTERNS=(
    r'/contact(?:[-_/]?us)?/?$', r'/get[-_/]?in[-_/]?touch/?$',
    r'/partnership', r'/partners', r'/business[-_/]?inquir', r'/general[-_/]?inquir',
    r'/corporate', r'/about/.+contact',
)
BUYER_SIGNAL_TERMS=(
    'founder','co-founder','ceo','owner','managing director','operations','head of ops','coo',
    'we are hiring','we’re hiring','join our team','careers','open roles',
    'case studies','clients','our team','team of','employees','locations',
    'automation','ai','artificial intelligence','crm','hubspot','salesforce','make.com','zapier','n8n',
    'retainer','performance marketing','paid media','seo','ppc','creative','branding','web design'
)


def route_class(url:str)->str:
    p=(urlparse(url).path or '/').lower()
    if any(re.search(x,p) for x in BAD_ROUTE_PATTERNS): return 'BAD_INBOUND_BUYER_FORM'
    if any(re.search(x,p) for x in GOOD_ROUTE_PATTERNS): return 'GOOD_NEUTRAL_OR_PARTNERSHIP'
    return 'UNKNOWN'


def buyer_state_score(text:str)->int:
    low=(text or '').lower()
    score=0
    # Evidence of a real operating agency and potential systems pain/capacity.
    if any(x in low for x in ('our team','meet the team','leadership','founder','ceo','owner')): score+=20
    if any(x in low for x in ('case studies','our clients','clients include','portfolio')): score+=15
    if any(x in low for x in ('careers','we are hiring','we’re hiring','open roles','join our team')): score+=20
    if any(x in low for x in ('hubspot','salesforce','crm','zapier','make.com','n8n','automation','artificial intelligence',' ai ')): score+=15
    if any(x in low for x in ('retainer','paid media','performance marketing','seo','ppc','creative agency','branding agency','digital agency')): score+=10
    if any(x in low for x in ('multiple locations','offices in','global agency','international agency')): score+=10
    return min(score,100)


def sendable(url:str, site_text:str, threshold:int=35):
    rc=route_class(url)
    score=buyer_state_score(site_text)
    return rc=='GOOD_NEUTRAL_OR_PARTNERSHIP' and score>=threshold, rc, score
