import csv
import json
import random
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

APP_TITLE = "キャリアのステージはどこだ？"
OUTPUT_CSV = Path("responses.csv")

LIKERT = [
    (1, "全く関心がない"),
    (2, "あまり関心がない"),
    (3, "少しは関心がある"),
    (4, "ある程度関心がある"),
    (5, "大いに関心がある"),
]

LIKERT_LABEL_HTML = {
    1: "全く関心が<br>ない",
    2: "あまり関心が<br>ない",
    3: "少しは関心が<br>ある",
    4: "ある程度関心が<br>ある",
    5: "大いに関心が<br>ある",
}

STAGES = {
    "探索期": {
        "title": "あなたは探索期かも",
        "items": [
            "自分に最も適した仕事分野を見つけること",
            "自分が興味を持てる仕事分野を見つけること",
            "自分が選んだキャリアの分野で仕事を始めること",
        ],
        "feedback": "探索段階は、一般には15歳から25歳の間が該当する。しかし、より後の時期に再び経験することも、しばしばある。結晶化、特定化、実行化という3つの下位段階があり、結晶化段階では、職業選択の幅を絞り込み、自分がどのような仕事に就きたいのかを考える。特定化段階では、自分が検討している職業の中で、どの職業が最も適しているのかを決定する。実行化段階では、個人がキャリア目標を達成するための計画を立て、雇用主を特定し、面接のプロセスを開始する。",
    },
    "確立期": {
        "title": "あなたは確立期かも",
        "items": [
            "長く続けられる定職に就くこと",
            "仕事において、際立って高い見識や技能を身につけること",
            "これまで確立した分野で、どう昇進・成功していくかを計画すること",
        ],
        "feedback": "確立段階はふつう25歳から45歳の間に生じるが、もっと後に再び経験することがある。下位段階は、安定化、定着化、前進化である。安定化段階は、個人が一定期間その仕事にとどまることを期待して働き始めるときに生じる。仕事に落ち着き始め、自分が選んだ仕事で成功するための技能を持っているかどうかを見極める。定着化段階では、個人は自分の仕事により慣れ、安心感や安定感を持つようになる。前進化段階では、個人は高い業績を上げることや昇進することに焦点を当てる。",
    },
    "維持期": {
        "title": "あなたは維持期かも",
        "items": [
            "同じ分野（専門、職場、部門）の人々からの尊敬を保つこと",
            "仕事に関する新しい技術や方法について勉強会やセミナーに参加すること",
            "仕事で取り組むべき新たな問題を見極めること",
        ],
        "feedback": "維持段階は、45歳から65歳の間に生じ、保持、更新、革新という下位段階を含む。保持段階では、個人は現在の仕事を維持することに関心を持つ傾向がある。更新段階では、個人は、自分の分野で有効に働くために必要な最新の職務技能を身につけるべく、継続教育、技能訓練ワークショップ、その他の機会を追求する。革新段階では、個人はキャリアに関連する課題を遂行するための、創造的な、あるいはより効果的な方法を探す。",
    },
    "解放期": {
        "title": "あなたは解放期かも",
        "items": [
            "自分の仕事をより容易に進める方法を開発すること",
            "退職に向けて十分に計画すること",
            "退職後に住むための場所を持つこと",
        ],
        "feedback": "解放段階はおよそ65歳以降に生じるが、今日では、退職計画は65歳よりもずっと早く始まることがあるかもしれない。実際、キャリアを始めたばかりの人であっても、個人退職口座やその他の退職給付制度を通じて「先を見越して計画する」ことを勧められることが多い。離脱段階の下位段階には、減速、退職計画、退職生活が含まれる。減速段階では、仕事のペースを落とし、退職について考え始める。退職計画段階は、個人が退職後の経済的側面および社会的側面について計画を立てるときに生じる。退職生活段階は、個人が仕事をやめ、退職に向けて立てた計画を実行に移すときに生じる。",
    },
}

GENDER_OPTIONS = {
    0: "男性",
    1: "女性",
    2: "その他",
}


def stage_scores(answers: dict[str, int]) -> dict[str, float]:
    scores = {}
    for stage, data in STAGES.items():
        vals = [answers[f"{stage}_{i}"] for i in range(len(data["items"]))]
        scores[stage] = sum(vals) / len(vals)
    return scores


def judge(answers: dict[str, int]):
    values = list(answers.values())
    if len(set(values)) == 1:
        return "判定不能", [], {}
    scores = stage_scores(answers)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_stages = [stage for stage, _ in ranked[:2]]
    return "判定可", top_stages, scores


def append_local_csv(row: dict):
    file_exists = OUTPUT_CSV.exists()
    with OUTPUT_CSV.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def append_google_sheet(row: dict) -> bool:
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except Exception:
        return False

    if "SPREADSHEET_ID" not in st.secrets or "gcp_service_account" not in st.secrets:
        return False

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    service_account_info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    client = gspread.authorize(creds)
    worksheet_name = st.secrets.get("WORKSHEET_NAME", "Sheet1")
    ws = client.open_by_key(st.secrets["SPREADSHEET_ID"]).worksheet(worksheet_name)

    existing = ws.get_all_values()
    if not existing:
        ws.append_row(list(row.keys()))
    ws.append_row(list(row.values()))
    return True


def save_response(row: dict):
    try:
        if append_google_sheet(row):
            return "Google Sheets"
    except Exception as e:
        st.warning(f"Google Sheetsへの保存に失敗したため、CSVに保存します: {e}")
    append_local_csv(row)
    return "CSV"


def render_likert_ruler():
    labels_html = "".join(f"<div>{LIKERT_LABEL_HTML[value]}</div>" for value, _ in LIKERT)
    ticks_html = "".join("<div class='likert-tick'></div>" for _ in LIKERT)
    numbers_html = "".join(f"<div>{value}</div>" for value, _ in LIKERT)
    st.markdown(
        f"""
<div class="likert-ruler">
  <div class="likert-labels">{labels_html}</div>
  <div class="likert-line">{ticks_html}</div>
  <div class="likert-numbers">{numbers_html}</div>
</div>
""",
        unsafe_allow_html=True,
    )


st.set_page_config(page_title=APP_TITLE, page_icon="🧭", layout="centered")
st.title(APP_TITLE)

st.markdown(
    """
<style>
.likert-ruler {
  max-width: 760px;
  margin: 8px 0 0 0;
}
.likert-labels,
.likert-numbers {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  text-align: center;
  align-items: end;
}
.likert-labels div {
  font-size: 0.88rem;
  line-height: 1.25;
  min-height: 2.65em;
  padding: 0 4px;
  white-space: nowrap;
}
.likert-line {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  align-items: center;
  margin-top: 4px;
  height: 22px;
  position: relative;
}
.likert-line::before {
  content: "";
  position: absolute;
  left: 10%;
  right: 10%;
  top: 10px;
  border-top: 2px solid #666;
}
.likert-tick {
  justify-self: center;
  width: 0;
  height: 22px;
  border-left: 2px solid #666;
  z-index: 1;
}
.likert-numbers div {
  font-size: 0.94rem;
  line-height: 1;
  margin-top: 0;
}
div[data-testid="stRadio"] {
  max-width: 760px !important;
  width: 100% !important;
}
div[data-testid="stRadio"] div[role="radiogroup"] {
  display: grid !important;
  grid-template-columns: repeat(5, 1fr) !important;
  column-gap: 0 !important;
  max-width: 760px !important;
  width: 100% !important;
  margin-top: -6px !important;
  margin-bottom: 34px !important;
}
div[data-testid="stRadio"] div[role="radiogroup"] label {
  width: 100% !important;
  min-width: 0 !important;
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  padding: 0 !important;
  margin: 0 !important;
}
div[data-testid="stRadio"] div[role="radiogroup"] label > div:first-child {
  margin-right: 0 !important;
}
div[data-testid="stRadio"] div[role="radiogroup"] p {
  display: none !important;
}
.question-text {
  margin-top: 20px;
  margin-bottom: 2px;
}
</style>
""",
    unsafe_allow_html=True,
)

with st.form("career_stage_form"):
    gender = st.selectbox(
        "性別を教えてください",
        options=list(GENDER_OPTIONS.keys()),
        format_func=lambda x: f"{x}={GENDER_OPTIONS[x]}",
        index=None,
        placeholder="選択してください",
    )
    age = st.selectbox(
        "年齢を教えてください",
        options=list(range(15, 100)),
        index=None,
        placeholder="選択してください",
    )
    org_count = st.selectbox(
        "今の勤務先は何社目（何組織目）ですか？",
        options=list(range(0, 21)),
        index=None,
        placeholder="選択してください",
        help="就職経験がない場合は0、最初の就職先に継続勤務中なら1を選択してください。",
    )

    st.markdown("---")
    st.write("以下12の課題について、あなたが現在どの程度の関心を持っているかを数字で選択してください。")

    answers = {}
    all_items = []
    for stage, data in STAGES.items():
        for i, item in enumerate(data["items"]):
            all_items.append({"stage": stage, "i": i, "item": item})

    if "question_order" not in st.session_state:
        order = list(range(len(all_items)))
        random.shuffle(order)
        st.session_state.question_order = order

    q_no = 1
    for idx in st.session_state.question_order:
        q = all_items[idx]
        key = f"{q['stage']}_{q['i']}"
        st.markdown(f"<div class='question-text'>Q{q_no}. {q['item']}</div>", unsafe_allow_html=True)
        render_likert_ruler()
        ans = st.radio(
            f"Q{q_no}. {q['item']} 回答",
            options=[x[0] for x in LIKERT],
            format_func=lambda x: "",
            horizontal=True,
            index=None,
            key=key,
            label_visibility="collapsed",
        )
        answers[key] = ans
        q_no += 1

    submitted = st.form_submit_button("結果を見る")

if submitted:
    missing_face = gender is None or age is None or org_count is None
    missing_main = any(v is None for v in answers.values())

    if missing_face or missing_main:
        st.error("未回答の項目があります。すべて回答してください。")
    else:
        status, top_stages, scores = judge(answers)
        now = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M:%S")

        flat_answers = {}
        q_no = 1
        for stage, data in STAGES.items():
            for i, item in enumerate(data["items"]):
                flat_answers[f"Q{q_no}"] = answers[f"{stage}_{i}"]
                q_no += 1

        result_titles = [STAGES[s]["title"] for s in top_stages]
        feedback_texts = [STAGES[s]["feedback"] for s in top_stages]

        row = {
            "回答日時": now,
            "性別コード": gender,
            "性別": GENDER_OPTIONS[gender],
            "年齢": age,
            "勤務先_何社目_何組織目": org_count,
            **flat_answers,
            "判定": status,
            "上位1": top_stages[0] if len(top_stages) > 0 else "",
            "上位2": top_stages[1] if len(top_stages) > 1 else "",
            "FBタイトル": " / ".join(result_titles),
            "FB本文": "\n\n".join(feedback_texts),
            "ステージ平均_JSON_管理用": json.dumps(scores, ensure_ascii=False),
        }
        saved_to = save_response(row)

        st.success("回答を記録しました。")
        if status == "判定不能":
            st.warning("判定不能です。すべて同じ点数が選択されているため、結果を表示できません。")
        else:
            st.subheader("結果")
            for stage in top_stages:
                st.markdown(f"### {STAGES[stage]['title']}")
                st.write(STAGES[stage]["feedback"])
        st.caption(f"保存先: {saved_to}")
