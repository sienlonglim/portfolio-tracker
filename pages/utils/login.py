import streamlit as st


def check_login():
    if st.session_state.get("authed"):
        return True

    st.title("🔒 Login")
    with st.form("login"):
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        ok = st.form_submit_button("Sign in")
    if ok:
        creds = st.secrets["auth"]
        if user == creds["username"] and pw == creds["password"]:
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("Wrong username or password.")
    return False
