import streamlit as st
import os
import json
import time
import io
from google import genai
from google.genai import types
from anthropic import Anthropic
import docx

# 페이지 기본 설정
st.set_page_config(
    page_title="Dual-AI Cross Research Pipeline",
    page_icon="🔬",
    layout="wide"
)

CONFIG_FILE = "user_config.json"

# ==========================================
# 0. 서비스 전용 접속 비밀번호 설정 (원하시는 값으로 변경하세요)
# ==========================================
ACCESS_PASSWORD = "wqlab"  # <-- 이 부분을 원하는 비밀번호로 바꾸세요!

if "is_master_auth" not in st.session_state:
    st.session_state.is_master_auth = False

# 비밀번호가 인증되지 않았다면 진입 차단 화면 표시
if not st.session_state.is_master_auth:
    st.title("🔒 제한된 연구 분석 파이프라인")
    st.markdown("이 프로그램은 승인된 사용자만 이용할 수 있습니다. 접속 비밀번호를 입력해 주세요.")
    
    pw_input = st.text_input("서비스 접속 비밀번호", type="password", placeholder="비밀번호를 입력하세요")
    if st.button("🔐 접속하기", type="primary"):
        if pw_input == ACCESS_PASSWORD:
            st.session_state.is_master_auth = True
            st.rerun()
        else:
            st.error("❌ 비밀번호가 올바르지 않습니다.")
    st.stop()  # 비밀번호가 틀리면 아래 코드가 실행되지 않고 멈춤

# ==========================================
# 1. 설정 및 로그인 관련 함수
# ==========================================
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(config_data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)

def clear_config():
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)

saved_cfg = load_config()

if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False

if "gemini_api_key" not in st.session_state:
    st.session_state.gemini_api_key = ""
if "claude_api_key" not in st.session_state:
    st.session_state.claude_api_key = ""

if "remember_info" not in st.session_state:
    st.session_state.remember_info = saved_cfg.get("remember_info", False)
if "gemini_model" not in st.session_state:
    st.session_state.gemini_model = saved_cfg.get("gemini_model", "")
if "claude_model" not in st.session_state:
    st.session_state.claude_model = saved_cfg.get("claude_model", "")

if "final_output" not in st.session_state:
    st.session_state.final_output = ""

def create_word_document(text_content):
    doc = docx.Document()
    doc.add_heading("AI Dual-Agent 교차 연구 검증 결과", level=1)
    
    for line in text_content.split("\n"):
        if line.startswith("## "):
            doc.add_heading(line.replace("## ", ""), level=2)
        elif line.startswith("# "):
            doc.add_heading(line.replace("# ", ""), level=1)
        else:
            if line.strip():
                doc.add_paragraph(line)
            else:
                doc.add_paragraph()
                
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# ==========================================
# 2. 사이드바 (로그인 과정 제어)
# ==========================================
with st.sidebar:
    st.title("⚙️ 계정 및 시스템 설정")
    
    if st.session_state.is_logged_in:
        st.success("✅ 로그인 완료")
        st.info(f"📌 **Gemini 모델:**\n`{st.session_state.gemini_model}`\n\n📌 **Claude 모델:**\n`{st.session_state.claude_model}`")
        
        if st.button("🔓 로그아웃 / 설정 변경", use_container_width=True):
            st.session_state.is_logged_in = False
            st.session_state.gemini_api_key = ""
            st.session_state.claude_api_key = ""
            st.session_state.final_output = ""
            st.rerun()
    else:
        st.subheader("1. API 키 입력")
        gemini_key_input = st.text_input("Gemini API 키", type="password", placeholder="API 키를 입력하세요", key="gemini_key_input_box")
        claude_key_input = st.text_input("Claude API 키", type="password", placeholder="API 키를 입력하세요", key="claude_key_input_box")
        
        st.markdown("🔗 **API 키 발급 바로가기**")
        col_link1, col_link2 = st.columns(2)
        with col_link1:
            st.link_button("Google AI Studio", "https://aistudio.google.com/app/apikey", use_container_width=True)
        with col_link2:
            st.link_button("Anthropic 콘솔", "https://console.anthropic.com/", use_container_width=True)

        st.markdown("---")
        st.subheader("2. 모델 설정")
        gemini_mod_input = st.text_input("Gemini 모델명", value=st.session_state.gemini_model, placeholder="예: gemini-2.5-flash", key="gemini_mod_box")
        claude_mod_input = st.text_input("Claude 모델명", value=st.session_state.claude_model, placeholder="예: claude-sonnet-5", key="claude_mod_box")
        
        @st.dialog("🔍 사용 가능한 모델 목록 확인법")
        def show_model_guide():
            st.markdown("""
            ### 파이썬 명령어로 모델 목록 즉시 확인하기
            **1. CMD(명령 프롬프트) 창 열기:** `Win + R` 후 `cmd` 입력

            **2. Gemini 모델 목록 확인:**
            ```cmd
            py -c "from google import genai; client = genai.Client(api_key='본인_GEMINI_KEY'); print([m.name.replace('models/', '') for m in client.models.list()])"
            ```

            **3. Claude 모델 목록 확인:**
            ```cmd
            py -c "from anthropic import Anthropic; client = Anthropic(api_key='본인_CLAUDE_KEY'); print([m.id for m in client.models.list()])"
            ```
            """)

        if st.button("❓ 모델명을 모르시나요?", use_container_width=True):
            show_model_guide()

        st.markdown("---")
        remember_info_toggle = st.toggle("💾 설정 정보 저장 (다음 접속 시 모델명 자동 채우기)", value=st.session_state.remember_info)

        if st.button("🔑 로그인 / 설정 완료", type="primary", use_container_width=True):
            if not gemini_key_input or not claude_key_input:
                st.error("Gemini API 키와 Claude API 키를 모두 입력해 주세요.")
            elif not gemini_mod_input or not claude_mod_input:
                st.error("Gemini 모델명과 Claude 모델명을 모두 입력해 주세요.")
            else:
                st.session_state.gemini_api_key = gemini_key_input
                st.session_state.claude_api_key = claude_key_input
                st.session_state.gemini_model = gemini_mod_input
                st.session_state.claude_model = claude_mod_input
                st.session_state.remember_info = remember_info_toggle
                st.session_state.is_logged_in = True
                
                if remember_info_toggle:
                    save_config({
                        "remember_info": True,
                        "gemini_model": gemini_mod_input,
                        "claude_model": claude_mod_input
                    })
                else:
                    clear_config()
                st.rerun()

# ==========================================
# 3. 메인 인터페이스 (탭 구조)
# ==========================================
st.title("🔬 AI Dual-Agent 교차 연구 검증 파이프라인")

tab_main, tab_admin, tab_troubleshoot = st.tabs(["🚀 연구 실행", "🛠️ 관리자 탭", "🚨 예외 대처 가이드"])

# ------------------------------------------
# TAB 1: 연구 실행
# ------------------------------------------
with tab_main:
    if not st.session_state.is_logged_in:
        st.warning("👈 왼쪽 사이드바에서 API 키 및 모델 설정 확인 후 [🔑 로그인 / 설정 완료] 버튼을 눌러주세요.")
    else:
        st.subheader("1. 연구 주제 및 분석 파일 업로드")
        
        user_topic = st.text_area("연구 주제 / 핵심 분석 가설 입력", height=120)
        uploaded_file = st.file_uploader("참고 문헌 / 기획서 문서 업로드 (.docx)", type=["docx"])
        
        start_btn = st.button("🔥 파이프라인 실행 시작", type="primary", use_container_width=True)

        if start_btn:
            if not user_topic:
                st.warning("연구 주제를 입력해 주세요.")
            else:
                status_container = st.status("🚀 결과 도출 중... 파이프라인을 가동합니다.", expanded=True)
                
                gemini_client = genai.Client(api_key=st.session_state.gemini_api_key)
                claude_client = Anthropic(api_key=st.session_state.claude_api_key)

                def safe_call_gemini(contents_payload, sys_prompt):
                    max_retries = 5
                    for attempt in range(1, max_retries + 1):
                        try:
                            res = gemini_client.models.generate_content(
                                model=st.session_state.gemini_model,
                                contents=contents_payload,
                                config=types.GenerateContentConfig(
                                    system_instruction=sys_prompt,
                                    temperature=0.7,
                                    max_output_tokens=8000,
                                )
                            )
                            return res.text
                        except Exception as e:
                            err_str = str(e)
                            if any(k in err_str for k in ["503", "429", "UNAVAILABLE", "Overloaded", "RESOURCE_EXHAUSTED"]):
                                wait_time = 10
                                for remaining in range(wait_time, 0, -1):
                                    status_container.warning(f"⏳ [Gemini 서버 과부하/토큰 대기 중] {remaining}초 후 재시도합니다... (시도 {attempt}/{max_retries})")
                                    time.sleep(1)
                            else:
                                status_container.error(f"❌ Gemini 오류: {e}")
                                raise e
                    raise Exception("Gemini API 재시도 횟수를 초과했습니다.")

                def safe_call_claude(prompt, sys_prompt):
                    max_retries = 5
                    for attempt in range(1, max_retries + 1):
                        try:
                            res = claude_client.messages.create(
                                model=st.session_state.claude_model,
                                max_tokens=8000,
                                system=sys_prompt,
                                messages=[{"role": "user", "content": prompt}]
                            )
                            text_parts = [b.text for b in res.content if getattr(b, 'type', None) == 'text']
                            return "\n".join(text_parts)
                        except Exception as e:
                            err_str = str(e)
                            if any(k in err_str for k in ["429", "529", "overloaded", "rate_limit"]):
                                wait_time = 10
                                for remaining in range(wait_time, 0, -1):
                                    status_container.warning(f"⏳ [Claude 서버 과부하/토큰 대기 중] {remaining}초 후 재시도합니다... (시도 {attempt}/{max_retries})")
                                    time.sleep(1)
                            else:
                                status_container.error(f"❌ Claude 오류: {e}")
                                raise e
                    raise Exception("Claude API 재시도 횟수를 초과했습니다.")

                try:
                    file_text = ""
                    if uploaded_file is not None:
                        status_container.write("📄 업로드된 문서 분석 중...")
                        doc = docx.Document(uploaded_file)
                        file_text = "\n".join([p.text for p in doc.paragraphs])

                    status_container.write("💡 [1/4] Gemini: 초기 연구 아이디어 및 가설 생성 중...")
                    gemini_prompt = f"주제: {user_topic}\n\n[참고 문서 내용]\n{file_text[:4000]}"
                    gemini_res = safe_call_gemini(gemini_prompt, "학술 연구 기획 전문가로서 독창적 가설과 방법론을 제안하세요.")
                    
                    status_container.write("🔍 [2/4] Claude: 메커니즘 분석 및 학술적 허점 교차 고찰 중...")
                    claude_prompt = f"Gemini의 다음 제안에 대해 학술적 맹점 및 비판적 고찰을 수행하세요:\n\n{gemini_res}"
                    claude_res = safe_call_claude(claude_prompt, "상호 심의 피어 리뷰어로서 독창적이고 날카로운 비판을 제공하세요.")

                    status_container.write("🤝 [3/4] 토론 통합 및 최종 합성 중...")
                    st.session_state.final_output = f"## 1. Gemini 제안\n{gemini_res}\n\n## 2. Claude 교차 검증 및 비판\n{claude_res}"

                    status_container.update(label="✅ 분석 완료! 결과가 도출되었습니다.", state="complete", expanded=False)

                except Exception as pipeline_err:
                    status_container.update(label="💥 파이프라인 중단됨", state="error")
                    st.error(f"오류가 발생하여 프로세스가 중단되었습니다: {pipeline_err}")

        if st.session_state.final_output:
            st.markdown("---")
            st.success("🎉 결과 도출 완료!")
            
            col_dl, col_info = st.columns([1, 2])
            with col_dl:
                word_file = create_word_document(st.session_state.final_output)
                st.download_button(
                    label="📥 워드 파일로 다운로드 (.docx)",
                    data=word_file,
                    file_name="research_analysis_result.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
            with col_info:
                st.info("💡 우측 상단의 **복사 버튼(아이콘)**을 누르면 전체 텍스트가 클립보드에 복사됩니다.")

            st.markdown(st.session_state.final_output)
            st.markdown("### 📋 전체 텍스트 복사 영역")
            st.code(st.session_state.final_output, language="markdown")

# ------------------------------------------
# TAB 2: 관리자 탭
# ------------------------------------------
with tab_admin:
    st.subheader("🛠️ 시스템 현황 및 API 실시간 테스트")
    
    if not st.session_state.is_logged_in:
        st.warning("로그인 후 이용하실 수 있습니다.")
    else:
        col_admin1, col_admin2 = st.columns(2)
        with col_admin1:
            if st.button("🧪 Gemini API 연결 검증"):
                try:
                    c = genai.Client(api_key=st.session_state.gemini_api_key)
                    models = [m.name for m in c.models.list()]
                    st.success(f"Gemini 연결 성공! (사용 가능 모델 수: {len(models)}개)")
                except Exception as e:
                    st.error(f"Gemini 연결 실패: {e}")

        with col_admin2:
            if st.button("🧪 Claude API 연결 검증"):
                try:
                    c = Anthropic(api_key=st.session_state.claude_api_key)
                    models = [m.id for m in c.models.list()]
                    st.success(f"Claude 연결 성공! (사용 가능 모델 수: {len(models)}개)")
                except Exception as e:
                    st.error(f"Claude 연결 실패: {e}")

        st.markdown("---")
        st.subheader("📝 세션 상태 데이터 모니터링")
        st.json({
            "gemini_model": st.session_state.gemini_model,
            "claude_model": st.session_state.claude_model,
            "remember_info": st.session_state.remember_info,
            "is_logged_in": st.session_state.is_logged_in
        })

# ------------------------------------------
# TAB 3: 예기치 못한 오류 대처 가이드
# ------------------------------------------
with tab_troubleshoot:
    st.subheader("🚨 예기치 못한 오류 발생 시 대처 가이드")
    st.markdown("""
    | 에러 종류 | 주요 원인 | 즉각적인 해결 대처방안 |
    | :--- | :--- | :--- |
    | **`404 NOT_FOUND`** | 존재하지 않거나 만료된 모델명 입력 | 사이드바의 **'로그아웃/설정 변경'** 후 모델명 조회 가이드를 참조하여 정확한 모델명으로 수정 |
    | **`429 / RESOURCE_EXHAUSTED`** | 분당 API 호출 한도 초과 | 프로그램이 10초 대기 카운트다운 후 자동 재시도합니다. |
    | **`503 / UNAVAILABLE`** | Google/Anthropic 서버 측 일시적 과부하 | AI 서버 과부하 상황이므로 10~30초 후 다시 실행 버튼 클릭 |
    """)
