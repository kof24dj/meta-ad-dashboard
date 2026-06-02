import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount

load_dotenv()
ACCESS_TOKEN = os.getenv('META_ACCESS_TOKEN')
AD_ACCOUNT_ID = os.getenv('META_AD_ACCOUNT_ID')

FacebookAdsApi.init(access_token=ACCESS_TOKEN)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/campaign_stats")
def get_campaign_stats(start_date: str = None, end_date: str = None, account_ids: str = None):
    target_accounts = account_ids.split(",") if account_ids else [AD_ACCOUNT_ID]
    data_list = []
    
    # 🌟 修改為抓取 Ad 層級，這樣才能拿到「廣告素材名稱」
    # 同時保留 campaign_name 用於縣市/粉專分類
    fields = ['ad_name', 'campaign_name', 'actions', 'spend']
    
    if start_date and end_date:
        params = {'time_range': json.dumps({'since': start_date, 'until': end_date}), 'level': 'ad'}
    else:
        params = {'date_preset': 'last_7d', 'level': 'ad'}
    
    for acc_id in target_accounts:
        acc_id = acc_id.strip()
        if not acc_id: continue
            
        account = AdAccount(acc_id)
        try:
            # 增加 limit 確保大數據量時能抓完
            insights = account.get_insights(fields=fields, params=params)
            if insights:
                for item in insights:
                    actions = item.get('actions', [])
                    spend = float(item.get('spend', 0))
                    
                    def get_exact_action_value(actions_list, preferred_types):
                        if not actions_list: return 0
                        for p_type in preferred_types:
                            for act in actions_list:
                                if act.get('action_type') == p_type:
                                    return int(act.get('value', 0))
                        return 0

                    comments = get_exact_action_value(actions, ['comment'])
                    # 詢問數 / 傳訊數
                    messages = get_exact_action_value(actions, [
                        'onsite_conversion.messaging_conversation_started_7d', 
                        'messaging_conversation_started_7d'
                    ])

                    if spend > 0 or comments > 0 or messages > 0:
                        data_list.append({
                            "adName": item.get('ad_name', '未命名廣告'),
                            "campaignName": item.get('campaign_name', '未命名活動'),
                            "comments": comments,
                            "messages": messages,
                            "spend": spend
                        })
        except Exception as e:
            print(f"帳號 {acc_id} 抓取失敗: {e}")
            continue
            
    return {"status": "success", "data": data_list}