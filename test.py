import streamlit as st
from datetime import datetime, date
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib

# サイドバーの設定
app_mode = st.sidebar.selectbox("モードを選択してください", ["勤怠登録アプリ", "勤怠登録アプリ（管理用）"])

# SQLite3データベースに接続
conn = sqlite3.connect('attendance.db')
conn.execute('''
 CREATE TABLE IF NOT EXISTS attendance ( 
     id INTEGER PRIMARY KEY, 
     employee_id INTEGER NOT NULL, 
     date DATE NOT NULL, 
     status TEXT NOT NULL, 
     check_in_time TIMESTAMP,
     check_out_time TIMESTAMP
) 
''')
conn.commit()
cursor = conn.cursor()

if app_mode == "勤怠登録アプリ":
    # Streamlitアプリの設定
    st.title("勤怠登録アプリ")

    employee_id = st.number_input("社員IDを入力してください", min_value=1, step=1)
    status = st.selectbox("状態を選択してください", ["出勤", "退勤"])
    submit = st.button("登録")

    if submit:
        if status == "出勤":
            check_in_time = datetime.now()
            cursor.execute(
                "INSERT INTO attendance (employee_id, date, status, check_in_time) VALUES (?, ?, ?, ?)",
                (employee_id, check_in_time.date(), status, check_in_time)
            )
        elif status == "退勤":
            check_out_time = datetime.now()
            cursor.execute(
                "UPDATE attendance SET status = ?, check_out_time = ? WHERE employee_id = ? AND date = ?",
                (status, check_out_time, employee_id, check_out_time.date())
            )

        conn.commit()
        st.success("登録が完了しました")

        # Retrieve registration data from the database
        cursor.execute("SELECT * FROM attendance WHERE employee_id = ?", (employee_id,))
        data = cursor.fetchall()

        # Display registration status in a table
        st.subheader(f"{employee_id}の登録状況")
        if len(data) > 0:
            # Retrieve the latest registration data for the employee
            # cursor.execute("SELECT date, status, check_in_time, check_out_time FROM attendance WHERE employee_id = ? ORDER BY date DESC LIMIT 1", (employee_id,))
            cursor.execute("SELECT date, status, check_in_time, check_out_time FROM attendance WHERE employee_id = ? ORDER BY date DESC LIMIT 1", (employee_id,))
            latest_data = cursor.fetchall()

            # Display the latest registration data
            if latest_data:
                # Convert the data to a DataFrame
                df = pd.DataFrame(latest_data, columns=["日付", "状態", "出勤時間", "退勤時間"])
                st.write(df)

        else:
            st.info("まだ登録がありません")

else:
    # Streamlitアプリの設定
    st.title("勤怠登録アプリ（管理用）")

    # CSVインポート機能
    uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type="csv")

    if uploaded_file is not None:
        df_import = pd.read_csv(uploaded_file)
        # df_import["date"] = pd.to_datetime(df_import["date"])
        # df_import["check_in_time"] = pd.to_datetime(df_import["check_in_time"])
        # df_import["check_out_time"] = pd.to_datetime(df_import["check_out_time"])
        
        # データベースへのインポート処理
        for _, row in df_import.iterrows():
            print(row)
            print(row["date"])
            print(row["check_in_time"])
            print(row["check_out_time"])
            cursor.execute(
                "INSERT INTO attendance (employee_id, date, status, check_in_time, check_out_time) VALUES (?, ?, ?, ?, ?)",
                (row["employee_id"], row["date"], row["status"], row["check_in_time"], row["check_out_time"])
            )
        
        conn.commit()
        st.success("CSVファイルのインポートが完了しました")

    # Retrieve registration data from the database
    cursor.execute("SELECT * FROM attendance")
    data = cursor.fetchall()

    # Display registration status in a table
    st.subheader("登録状況")
    if len(data) > 0:
        # Convert the data to a DataFrame
        df = pd.DataFrame(data, columns=["ID", "社員ID", "日付", "状態", "出勤時間", "退勤時間"]).sort_values(["日付", "社員ID"]).reset_index(drop=True)
        st.write(df.loc[:,["社員ID", "日付", "状態", "出勤時間", "退勤時間"]])

        # # Display the number of registrations by status
        # status_count = df["状態"].value_counts()
        # st.write("登録数", status_count)

        # Display the number of registrations by employee
        # employee_count = df["社員ID"].value_counts()
        # st.write("社員ごとの登録数", employee_count)

        # # Retrieve the attendance data without check-in and check-out times
        # missing_data = df[df["出勤時間"].isnull() | df["退勤時間"].isnull()]

        # Display the attendance data without check-in and check-out times
        st.subheader("社員別勤怠情報(月別労働時間)")
        # Calculate monthly working hours by employee
        df["日付"] = pd.to_datetime(df["日付"])
        df["出勤時間"] = pd.to_datetime(df["出勤時間"])
        df["退勤時間"] = pd.to_datetime(df["退勤時間"])
        df["年月"] = df["日付"].dt.strftime('%Y-%m')
        df["労働時間"] = (df["退勤時間"] - df["出勤時間"]).dt.total_seconds() / 3600
        # Check if the column "社員ID" exists in the DataFrame
        df_a = df.pivot_table(index="社員ID", columns="年月", values="労働時間", aggfunc="sum")
        st.write(df_a)

        # グラフの準備
        fig, ax = plt.subplots(figsize=(10, 6))

        # 社員IDごとにデータをグループ化し、折れ線グラフでプロット
        for employee_id in df_a.index:
            df_employee = df_a.loc[employee_id]
            df_employee.sort_index(inplace=True)  # 年月でソート
            # 折れ線グラフでプロット
            ax.plot(df_employee.index, df_employee.values, marker='o', label=f"社員ID: {employee_id}")

        # グラフの装飾
        ax.set_title("全社員の月別労働時間")
        ax.set_xlabel("年月")
        ax.set_ylabel("労働時間（時間）")
        ax.legend()
        ax.grid(True)
        ax.set_ylim(150, None)  # Set the y-axis limit to 150 and let the upper limit be determined automatically
        plt.xticks(rotation=45)  # X軸のラベルを45度回転

        # Streamlitでグラフを表示
        st.pyplot(fig)


        fig, ax = plt.subplots(figsize=(10, 6))

        # 社員IDごとにデータをグループ化し、折れ線グラフでプロット
        for employee_id in df_a.index:
            df_employee = df_a.loc[employee_id]
            df_employee.sort_index(inplace=True)  # 年月でソート
            # 棒グラフでプロット
            ax.bar(df_employee.index, df_employee.values, width=0.4, alpha=0.5, label=f"社員ID: {employee_id} (Bar)")

        # グラフの装飾
        ax.set_title("全社員の月別労働時間")
        ax.set_xlabel("年月")
        ax.set_ylabel("労働時間（時間）")
        ax.legend()
        ax.grid(True)
        ax.set_ylim(150, None)  # Set the y-axis limit to 150 and let the upper limit be determined automatically
        plt.xticks(rotation=45)  # X軸のラベルを45度回転

        # Streamlitでグラフを表示
        st.pyplot(fig)

        # 社員IDの選択
        employee_id_to_edit = st.selectbox("修正する社員IDを選択してください", df['社員ID'].unique(), index=0)

        # 選択された社員IDに対応する日付を選択
        if employee_id_to_edit:
            df_employee = df[df['社員ID'] == employee_id_to_edit]
            date_to_edit = st.selectbox("修正する日付を選択してください", df_employee['日付'].unique())
            # 修正機能の拡張
            if date_to_edit:
                df_employee_date_to_edit = df_employee[df_employee['日付'] == date_to_edit]
                st.write("現在のデータ:", df_employee_date_to_edit)

                with st.form(key='edit_employee_date_form'):
                    new_start_time = st.time_input("新しい出勤時間を入力してください", value=df_employee_date_to_edit['出勤時間'].iloc[0])
                    modified_start_time = datetime.combine(date.today(), new_start_time)
                    print(f'***** modified_start_time:{modified_start_time}, type:{type(modified_start_time)}')

                    new_end_time = st.time_input("新しい退勤時間を入力してください", value=df_employee_date_to_edit['退勤時間'].iloc[0])
                    modified_end_time = datetime.combine(date.today(), new_end_time)
                    print(f'***** modified_end_time:{modified_end_time}, type:{type(modified_end_time)}')

                    submit_button = st.form_submit_button(label='修正')

                    if submit_button:
                        # データベースの更新処理
                        print(f'***** new_start_time:{new_start_time}, new_end_time:{new_end_time}, employee_id_to_edit:{employee_id_to_edit}, date_to_edit:{date_to_edit}')
                        cursor.execute("UPDATE attendance SET check_in_time = ?, check_out_time = ? WHERE employee_id = ? AND date = ?", (modified_start_time, modified_end_time, employee_id_to_edit, date_to_edit))
                        conn.commit()
                        st.success(f"社員ID {employee_id_to_edit} の {date_to_edit} のデータを修正しました。")

            # 登録機能の追加
            with st.form(key='add_employee_form'):
                new_employee_id = st.text_input("社員IDを入力してください")
                new_date = st.date_input("日付を選択してください")
                new_start_time = st.time_input("出勤時間を入力してください")

                new_end_time = st.time_input("退勤時間を入力してください")

                add_button = st.form_submit_button(label='登録')

                if add_button:
                    # データベースへの登録処理
                    cursor.execute("INSERT INTO attendance (employee_id, date, check_in_time, check_out_time) VALUES (?, ?, ?, ?)", (new_employee_id, new_date.strftime('%Y-%m-%d'), modified_start_time, modified_end_time))
                    conn.commit()
                    st.success(f"社員ID {new_employee_id} のデータを登録しました。")

            # 削除機能の追加
            with st.form(key='delete_employee_form'):
                employee_id_to_delete = st.selectbox("削除する社員IDを選択してください", df['社員ID'].unique(), index=0)
                date_to_delete = st.date_input("削除する日付を選択してください")
                delete_button = st.form_submit_button(label='削除')

                if delete_button:
                    # データベースからの削除処理
                    cursor.execute("DELETE FROM attendance WHERE employee_id = ? AND date = ?", (employee_id_to_delete, date_to_delete))
                    conn.commit()
                    st.success(f"社員ID {employee_id_to_delete} の {date_to_delete} のデータを削除しました。")
    else:
        st.info("まだ登録がありません")


# データベース接続を閉じる
cursor.close()
conn.close()
