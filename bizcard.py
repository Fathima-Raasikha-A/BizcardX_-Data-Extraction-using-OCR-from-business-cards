import streamlit as st
from streamlit_option_menu import option_menu
from PIL import Image
import easyocr
import psycopg2
import os
import cv2
import re
import pandas as pd

# SETTING PAGE CONFIGURATION
st.set_page_config(page_title= "BizCardX: Extracting Business Card Data with OCR ",
                   layout= "wide")
st.markdown("<h1 style='text-align: center; color: Red;'>BizCardX: Extracting Business Card Data with OCR</h1>", unsafe_allow_html=True)

# CREATING OPTION MENU
with st.sidebar:
    Option = option_menu(None, ["Home","Upload & Extract","Alter / Delete"], 
                        icons=["house","cloud-upload","pencil-square"],
                        default_index=0)
    
# INITIALIZING THE EasyOCR READER
reader = easyocr.Reader(['en'])

#CONNECTING WITH POSTGRESQL DATABASE
mydb = psycopg2.connect(
                        host='localhost',
                        user='postgres',
                        password='anasrazi',
                        database='bizcardx',
                        port='5432'
)
cursor = mydb.cursor()

# TABLE CREATION
create_query = '''CREATE TABLE IF NOT EXISTS Cards_Data (
                                                        id SERIAL PRIMARY KEY,
                                                        name text,
                                                        company_name text,
                                                        designation text,
                                                        mobile_no Varchar(50),
                                                        email text,
                                                        website text,
                                                        address text,
                                                        city text,
                                                        state text,
                                                        pincode Varchar(10),
                                                        image BYTEA
                                                    )'''

cursor.execute(create_query)
mydb.commit()

#FUNCTION FOR SAVING CARD TO FILE FOLDER
def save_card(card):
    with open(os.path.join('uploaded_cards', card.name), "wb") as f:
        f.write(card.getbuffer())

#FUNCTION FOR CONVERTING IMAGE TO BINARY TO UPLOAD TO SQL DATABASE
def img_to_binary(file):
    with open(file, 'rb') as file:
        binaryData=file.read()
    return binaryData

#STREAMLIT BACKEND
if Option=="Home":
    st.markdown("## :green[**Technologies Used :**] Python,easyOCR, Streamlit, PostgreSQL, Pandas")
    st.markdown("## :green[**Description :**] In this streamlit web application you can upload an image of a business card and extract relevant information from it using easyOCR library. You can view, modify or delete the extracted data in this application.")

elif Option=="Upload & Extract":
    st.markdown("### Upload a Business Card")
    uploaded_card=st.file_uploader("upload here",label_visibility="collapsed",type=["png","jpeg","jpg"])

    if uploaded_card is not None:
        save_card(uploaded_card)

        # DISPLAYING THE UPLOADED CARD
        col1,col2=st.columns(2)
        with col1:
            st.markdown("#     ")
            st.markdown("#     ")
            st.markdown("### You have uploaded the card")
            st.image(uploaded_card)


        # DISPLAYING THE CARD WITH EXTRACTED DATA
        with col2:
            st.markdown("#     ")
            st.markdown("#     ")
            with st.spinner("Please wait processing the image..."):
                st.markdown("### Image Processed and Data Extracted is as shown below")
        

        #easy OCR
        saved_img = os.getcwd()+ "\\" + "uploaded_cards"+ "\\"+ uploaded_card.name
        result = reader.readtext(saved_img,detail = 0,paragraph=False)

        #FUNCTION FOR COLLECTING ALL DATA FROM CARD
        def get_data(res):
            data = {"name" : [],
                    "company_name" : [],
                    "designation" : [],
                    "mobile_no" :[],
                    'email': [],
                    "website": [],
                    "address" : [],
                    "city" : [],
                    "state" : [],
                    "pincode" : [],
                    "image": img_to_binary(saved_img)}
            for ind, i in enumerate(res):
              #TO GET WEBSITE  
                if 'www' in i.lower() or "WWW" in i.lower():
                            data['website'].append(i)
                elif 'wwW' in i:
                    data["website"] = res[4] +"." + res[5]
                
                # TO GET EMAIL ID
                elif "@" in i:
                    data["email"].append(i)

                #TO GET MOBILE NUMBER
                elif "-" in i:
                    data["mobile_no"].append(i)
                    if len(data["mobile_no"]) ==2:
                        data["mobile_no"] = " & ".join(data["mobile_no"])

                # TO GET COMPANY NAME  
                elif ind== len(res)-2:
                    data["company_name"].append(i)
                # TO GET CARD HOLDER NAME
                elif ind == 0:
                    data["name"].append(i)

                # TO GET DESIGNATION
                elif ind == 1:
                    data["designation"].append(i)

                # TO GET AREA
                if re.findall('^[0-9].+, [a-zA-Z]+',i):
                    data["address"].append(i.split(',')[0])
                elif re.findall('[0-9] [a-zA-Z]+',i):
                    data["address"].append(i)

                # TO GET CITY NAME
                match1 = re.findall('.+St , ([a-zA-Z]+).+', i)
                match2 = re.findall('.+St., ([a-zA-Z]+).+', i)
                match3 = re.findall('^[E].*',i)
                if match1:
                    data["city"].append(match1[0])
                elif match2:
                    data["city"].append(match2[0])
                elif match3:
                    data["city"].append(match3[0])

                # TO GET STATE
                state_match = re.findall('[a-zA-Z]{9} +[0-9]',i)
                if state_match:
                        data["state"].append(i[:9])
                elif re.findall('^[0-9].+, ([a-zA-Z]+);',i):
                    data["state"].append(i.split()[-1])
                if len(data["state"])== 2:
                    data["state"].pop(0)

                # TO GET PINCODE        
                if len(i)>=6 and i.isdigit():
                    data["pincode"].append(i)
                elif re.findall('[a-zA-Z]{9} +[0-9]',i):
                    data["pincode"].append(i[10:])
            return data

        overall_data = get_data(result)

        #FUNCTION TO CREATE DATAFRAME
        def create_df(data):
            df = pd.DataFrame(data)
            return df
        
        df = create_df(overall_data)
        st.success("### The Extracted data is shown below")
        st.write(df)

        if st.button("Upload to Database"):
            for index, row in df.iterrows():
                try:
                    insert_query = '''INSERT INTO cards_data(name,
                                                            company_name,
                                                            designation,
                                                            mobile_no,
                                                            email,
                                                            website,
                                                            address,
                                                            city,
                                                            state,
                                                            pincode,
                                                            image
                                                        )
                                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                                                    '''
                    values = (row['name'],
                            row['company_name'],
                            row['designation'],
                            row['mobile_no'],
                            row['email'],
                            row['website'],
                            row['address'],
                            row['city'],
                            row['state'],
                            row['pincode'],
                            row['image']
                            )
                    cursor.execute(insert_query, values)
                    mydb.commit()
                    st.success("#### Uploaded to the database successfully!")
                except psycopg2.IntegrityError as e:
                    if e.pgcode == '23505':
                        st.write(f"#### Data has already present for the email {row['email']}")
                    else:
                        st.write(f"Error: {e}")

#UPDATE MENU
elif Option=="Alter / Delete":
    col1,col2,col3 = st.columns([2,3,1])
    col2.markdown('<h2 style="color: #BDF2B2;">Update or Delete the data here</h2>', unsafe_allow_html=True)
    column1,column2 = st.columns(2,gap="large")
    try:
        with column1:
            cursor.execute("SELECT name FROM cards_data")
            Names = cursor.fetchall()
            Card_names = {}
            for row in Names:
                Card_names[row[0]] = row[0]
            selected_card = st.selectbox("Select a card name to update", list(Card_names.keys()))
            st.markdown("#### Update or modify any data below")
            cursor.execute("select name,company_name,designation,mobile_no,email,website,address,city,state,pincode from cards_data WHERE name=%s",
                            (selected_card,))
            data1 = cursor.fetchone()
            
            name = st.text_input("Name", data1[0])
            company_name = st.text_input("Company_Name", data1[1])
            designation = st.text_input("Designation", data1[2])
            mobile_no = st.text_input("Mobile_No", data1[3])
            email = st.text_input("Email", data1[4])
            website = st.text_input("Website", data1[5])
            address = st.text_input("Address", data1[6])
            city = st.text_input("City",data1[7])
            state = st.text_input("State", data1[8])
            pincode = st.text_input("Pincode", data1[9])

            if st.button("Update the changes to database"):
                update_query = """UPDATE cards_data 
                                    SET 
                                        name=%s,
                                        company_name=%s,     
                                        designation=%s,
                                        mobile_no=%s,
                                        email=%s,
                                        website=%s,
                                        address=%s,
                                        city=%s,
                                        state=%s,
                                        pincode=%s
                                    WHERE 
                                        name=%s
                                """
                values = (
                    name,company_name, designation, mobile_no,
                    email, website, address, city, state, pincode, selected_card
                )
                cursor.execute(update_query, values)
                mydb.commit()
                st.success("##### Information updated in database successfully.")

        with column2:
            cursor.execute("SELECT name FROM cards_data")
            data2 = cursor.fetchall()
            Card_names = {}
            for row in data2:
                Card_names[row[0]] = row[0]
            selected_card = st.selectbox("Select a card name to Delete", list(Card_names.keys()))
            st.write(f"#### Do you want to delete :green[**{selected_card}'s**] card from database?")

            if st.button("Yes Delete this Business Card"):
                cursor.execute(f"DELETE FROM cards_data WHERE name='{selected_card}'")
                mydb.commit()
                st.success("#### Business card information for '{}' deleted from database.".format(selected_card))
    except:
        st.warning("##### There is no data available in the database")

    if st.button("View updated data"):
        cursor.execute("SELECT name, company_name, designation, mobile_no, email, website, address, city, state, pincode FROM cards_data")
        updated_data = cursor.fetchall()
        updated_df = pd.DataFrame(updated_data, columns=[ "Name", "Company_Name",  "Designation", "Mobile_No", "Email", "Website", "Address", "City", "State", "PinCode"])
        st.write(updated_df)