
import gradio as gr
import requests
import pandas as pd
import random
import string

# ==========================================
# 1. ORANGE MONEY API CONFIGURATION
# ==========================================
ORANGE_BASE_URL = "https://orange.com"
CLIENT_ID = "YOUR_ORANGE_DEVELOPER_CLIENT_ID"
CLIENT_SECRET = "YOUR_ORANGE_DEVELOPER_CLIENT_SECRET"
MERCHANT_KEY = "YOUR_SCHOOL_MERCHANT_KEY"

# ==========================================
# 2. IN-MEMORY DATABASE (Simulating School Ledger)
# ==========================================
SCHOOL_LEDGER = {
    "STU-2026-001": {"Name": "Alice Cooper", "Grade": "10th Grade", "Tuition Due (LRD)": 15000, "Status": "Unpaid", "Transaction ID": "N/A", "Email": "alice.cooper@example.com"},
    "STU-2026-002": {"Name": "Bob Marley", "Grade": "11th Grade", "Tuition Due (LRD)": 22000, "Status": "Unpaid", "Transaction ID": "N/A", "Email": "bob.marley@example.com"},
    "STU-2026-003": {"Name": "Charlie Parker", "Grade": "12th Grade", "Tuition Due (LRD)": 18000, "Status": "Unpaid", "Transaction ID": "N/A", "Email": "charlie.parker@example.com"}
}

TRASH_BIN_LEDGER_DICT = {}

LEDGER_PASSWORD = "17$&90"

# ==========================================
# 3. CORE LOGIC FUNCTIONS
# ==========================================

def get_access_token():
    return "mock_access_token"

def get_ledger_dataframe():
    data_list = []
    for s_id, info in SCHOOL_LEDGER.items():
        row = {"Student ID": s_id}
        row.update(info)
        data_list.append(row)
    return pd.DataFrame(data_list).set_index("Student ID", drop=False).sort_index()

def get_trash_bin_dataframe():
    data_list = []
    for s_id, info in TRASH_BIN_LEDGER_DICT.items():
        row = {"Student ID": s_id}
        row.update(info)
        data_list.append(row)
    if not data_list:
        return pd.DataFrame(columns=["Student ID", "Name", "Grade", "Tuition Due (LRD)", "Status", "Transaction ID", "Email", "Deleted Date"])
    df = pd.DataFrame(data_list)
    if 'Deleted Date' not in df.columns:
      df['Deleted Date'] = pd.to_datetime('now').strftime('%Y-%m-%d %H:%M:%S')
    return df.set_index("Student ID", drop=False).sort_index()

def generate_mock_txn_id():
    return 'OM_TX_' + ''.join(random.choices(string.digits, k=6))

def process_payment(student_id, phone_number, amount):
    if not student_id or not phone_number or not amount:
        return "⚠️ Error: Please fill in all fields.", get_ledger_dataframe(), get_trash_bin_dataframe()
    token = get_access_token()
    mock_txn_id = generate_mock_txn_id()
    webhook_message, current_ledger, current_trash_bin = simulate_network_webhook(student_id, mock_txn_id)
    return f"✅ USSD Push sent successfully to {phone_number}. {webhook_message}", current_ledger, current_trash_bin

def simulate_network_webhook(student_id, txn_id):
    if not student_id or not txn_id:
        return "⚠️ Error: Enter both a Student ID and a Mock Transaction ID.", get_ledger_dataframe(), get_trash_bin_dataframe()
    if student_id not in SCHOOL_LEDGER and student_id not in TRASH_BIN_LEDGER_DICT:
        SCHOOL_LEDGER[student_id] = {"Name": f"New Student {student_id}", "Grade": "N/A", "Tuition Due (LRD)": 0, "Status": "Unpaid", "Transaction ID": "N/A", "Email": "new.student@example.com"}
    elif student_id in TRASH_BIN_LEDGER_DICT:
        SCHOOL_LEDGER[student_id] = TRASH_BIN_LEDGER_DICT.pop(student_id)
    SCHOOL_LEDGER[student_id]["Status"] = "Paid"
    SCHOOL_LEDGER[student_id]["Transaction ID"] = txn_id

    # Call the email function if it's available
    try:
        # Assuming send_payment_confirmation_email is defined globally or imported
        # For this saved file, we need to ensure the email functions are also included
        # Or removed if not intended for the standalone Gradio app.
        # Since the context shows it's a separate cell (489233f0), I will NOT include it here
        # as it relies on colab userdata secrets, which won't be available in a standalone script.
        pass # Placeholder for email sending if needed with proper setup
    except NameError:
        pass # Email function not defined, gracefully skip

    return f"🎉 Success! Webhook simulation complete. Student {student_id} is marked as PAID.", get_ledger_dataframe(), get_trash_bin_dataframe()

def toggle_ledger_visibility(password):
    if password == LEDGER_PASSWORD:
        return (
            get_ledger_dataframe(),
            get_trash_bin_dataframe(),
            gr.update(visible=True),
            gr.update(value="Ledger revealed!", visible=True),
            gr.update(visible=True),
            gr.update(visible=True),
            gr.update(visible=True),
            gr.update(visible=True),
            gr.update(value="")
        )
    else:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            gr.update(visible=False),
            gr.update(value="Incorrect password.", visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(value="")
        )

def handle_ledger_edit(changes: gr.LikeData):
    global SCHOOL_LEDGER
    global TRASH_BIN_LEDGER_DICT

    edited_df = changes.value
    original_df = changes.orig_value

    original_students = set(original_df['Student ID'].tolist()) if not original_df.empty else set()
    edited_students = set(edited_df['Student ID'].tolist()) if not edited_df.empty else set()

    deleted_ids = original_students - edited_students

    if deleted_ids:
        print(f"[LEDGER EDIT] Detected deletion(s) of Student IDs: {deleted_ids}")
        for student_id in deleted_ids:
            if student_id in SCHOOL_LEDGER:
                TRASH_BIN_LEDGER_DICT[student_id] = SCHOOL_LEDGER.pop(student_id)
                TRASH_BIN_LEDGER_DICT[student_id]['Deleted Date'] = pd.to_datetime('now').strftime('%Y-%m-%d %H:%M:%S')

    if changes.delta:
        print(f"[LEDGER EDIT] Detected cell edit(s): {changes.delta}")
        for delta_change in changes.delta:
            row_idx = delta_change['row']
            col_name = delta_change['col']
            new_value = delta_change['value']

            student_id = edited_df.iloc[row_idx]['Student ID']

            if student_id in SCHOOL_LEDGER:
                SCHOOL_LEDGER[student_id][col_name] = new_value
            elif student_id in TRASH_BIN_LEDGER_DICT:
                TRASH_BIN_LEDGER_DICT[student_id][col_name] = new_value

    print(f"[LEDGER EDIT] Current SCHOOL_LEDGER: {SCHOOL_LEDGER}")
    print(f"[LEDGER EDIT] Current TRASH_BIN_LEDGER_DICT: {TRASH_BIN_LEDGER_DICT}")

    return get_ledger_dataframe(), get_trash_bin_dataframe()

def restore_from_trash(selected_rows):
    global SCHOOL_LEDGER
    global TRASH_BIN_LEDGER_DICT

    if not selected_rows:
        return gr.update(value="No student selected to restore."), get_ledger_dataframe(), get_trash_bin_dataframe()

    status_messages = []
    for row_data in selected_rows:
        student_id = row_data[0]
        if student_id in TRASH_BIN_LEDGER_DICT:
            restored_info = TRASH_BIN_LEDGER_DICT.pop(student_id)
            restored_info.pop('Deleted Date', None)
            SCHOOL_LEDGER[student_id] = restored_info
            status_messages.append(f"Student {student_id} restored.")
        else:
            status_messages.append(f"Student {student_id} not found in trash bin.")

    return gr.update(value="
".join(status_messages)), get_ledger_dataframe(), get_trash_bin_dataframe()

def permanently_delete_from_trash(selected_rows):
    global TRASH_BIN_LEDGER_DICT

    if not selected_rows:
        return gr.update(value="No student selected for permanent deletion."), get_trash_bin_dataframe(), get_ledger_dataframe()

    status_messages = []
    for row_data in selected_rows:
        student_id = row_data[0]
        if student_id in TRASH_BIN_LEDGER_DICT:
            TRASH_BIN_LEDGER_DICT.pop(student_id)
            status_messages.append(f"Student {student_id} permanently deleted.")
        else:
            status_messages.append(f"Student {student_id} not found in trash bin.")

    return gr.update(value="
".join(status_messages)), get_ledger_dataframe(), get_trash_bin_dataframe()


# ==========================================
# 4. GRADIO INTERFACE LAYOUT BUILDER
# ==========================================
with gr.Blocks() as demo:

    gr.Markdown("# 🍊 Orange Money Tuition Payment Hub")
    gr.Markdown("### Integrated Student Billing Portal & Administrative Dashboard Engine")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## 💳 Student Payment Portal")

            student_dropdown = gr.Textbox(
                label="Enter Student ID",
                placeholder="e.g., STU-2026-004"
            )
            phone_input = gr.Textbox(label="Orange Money Phone Number", placeholder="e.g., 077XXXXXXXX")
            amount_input = gr.Number(label="Tuition Amount to Pay (LRD)", value=15000)

            pay_btn = gr.Button("Initiate Secure MoMo Payment", variant="primary")
            portal_status_output = gr.Textbox(label="Transaction Action Output Log", interactive=False)

        with gr.Column(scale=1):
            gr.Markdown("## 📊 Bursar's Ledger Dashboard")

            password_input = gr.Textbox(label="Enter Password to View Ledger", type="password")
            reveal_ledger_btn = gr.Button("View Ledger")
            ledger_visibility_output = gr.Textbox(label="Ledger Access Status", interactive=False, visible=True)

            ledger_table = gr.DataFrame(value=pd.DataFrame(), interactive=True, visible=False)
            refresh_btn = gr.Button("🔄 Refresh Ledger Stream", variant="secondary", visible=False)

            trash_bin_markdown_comp = gr.Markdown("### 🗑️ Ledger Trash Bin", visible=False)
            trash_bin_table_comp = gr.DataFrame(value=pd.DataFrame(), visible=False, interactive=True)
            with gr.Row(visible=False) as trash_bin_buttons_row_comp:
                restore_btn = gr.Button("↩️ Restore Selected from Trash", variant="secondary")
                permanent_delete_btn = gr.Button("🗑️ Permanently Delete Selected", variant="stop")
            trash_bin_status_output_comp = gr.Textbox(label="Trash Bin Status", interactive=False, visible=False)


    gr.Markdown("---")
    with gr.Row():
        with gr.Column():
            gr.Markdown("### 🛠️ Developer Simulation Box")
            gr.Markdown("*Simulates the secure webhook callback dispatched from the Orange carrier network when a parent types their secret PIN.*")

            with gr.Row():
                sim_student_id = gr.Textbox(label="Target Student ID", placeholder="e.g., STU-2026-001", visible=False)
                sim_txn_id = gr.Textbox(label="Mock Transaction ID", placeholder="e.g., OM_TX_994118", visible=False)

            sim_btn = gr.Button("🚀 Simulate Orange Webhook Success Signal", visible=False)
            sim_output = gr.Textbox(label="Simulation System Engine Log", interactive=False, visible=False)

    # ==========================================
    # 5. COMPONENT EVENT HANDLERS
    # ==========================================

    pay_btn.click(
        fn=process_payment,
        inputs=[student_dropdown, phone_input, amount_input],
        outputs=[portal_status_output, ledger_table, trash_bin_table_comp]
    )

    refresh_btn.click(
        fn=get_ledger_dataframe,
        inputs=None,
        outputs=ledger_table
    )

    reveal_ledger_btn.click(
        fn=toggle_ledger_visibility,
        inputs=[password_input],
        outputs=[
            ledger_table,
            trash_bin_table_comp,
            refresh_btn,
            ledger_visibility_output,
            trash_bin_markdown_comp,
            trash_bin_table_comp,
            trash_bin_buttons_row_comp,
            trash_bin_status_output_comp,
            password_input
        ]
    )

    ledger_table.edit(
        fn=handle_ledger_edit,
        inputs=None,
        outputs=[ledger_table, trash_bin_table_comp]
    )

    restore_btn.click(
        fn=restore_from_trash,
        inputs=[trash_bin_table_comp],
        outputs=[trash_bin_status_output_comp, ledger_table, trash_bin_table_comp]
    )

    permanent_delete_btn.click(
        fn=permanently_delete_from_trash,
        inputs=[trash_bin_table_comp],
        outputs=[trash_bin_status_output_comp, ledger_table, trash_bin_table_comp]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0") # Removed theme=gr.themes.Soft(primary_hue="orange", secondary_hue="slate") for basic portability
