from flask import Flask, render_template, Response, request, jsonify
import json
import requests
import re
import os
import base64
from PIL import ImageGrab
import io
from datetime import datetime

app = Flask(__name__)

# Initialize the conversation with a system message
conversation = [
    {"role": "system", "content": """
    You are my personal AI. You are called NOVA.
    You are only allowed to respond in English no matter what langauge I use to talk to you.
    Act like me talking to you in another language is normal.
     
    Do not talk unnecessarily.

   -------------------------------------------------------------- 

    DO NOT FORMAT YOUR TEXT!! anything you say is said out loud using tts

    Your user can talk to you via text,speech recognition, or images. Keep in mind that the user is most likely using speech recognition and it may have issues.
    As my assistant, you have predefined functions you can call any time you feel the need to:
    You can see the users screen any time using SCREENSHOT().
     
    Do not ask "what would you like to do now?" every time.

    -If the user wants you to do something that isn't listed as a function try to come up with a clever solution for it
        for example: if you dont have access to time take a screenshot and try to read the time from the users taskbar OR
        if the user asks you to change the color of the window you run in  to red. try to find a way to do it like: RUN(color 4) which executes os.system(color 4) which changes the color to red.
    In short: try to come up with a solution before declaring you cant do something.
        
    1. OPEN(<app_name>) - To open predefined applications like Opera GX.
    2. SHUTDOWN() - To shut yourself down if asked.
    3. SCREENSHOT() - Takes a screenshot of the users screen and sends it to you.
    4. RUN(command) -run any win+r command CAN ALSO BE USED TO OPEN APPS!!!!! 
    5. MEMORY(memory to store) -store anything you deem necessary into a txt.
     
    To use these functions, your response must contain the function (for example, USER: shut yourself down. NOVA: Yes. SHUTDOWN()).

    Here are the instructions for using your functions:
    1. Opening apps: 
        - You are aware of some predefined applications that can be opened. For example:
            - opera
        - When I ask you to open an app, first check if the app name matches any predefined names.
        You can use the format OPEN(<app_name>) to open apps. 
        - If the app name is found in the list of predefined locations, open it directly using the path provided.
        - If the app name is not in the list, try opening it using the RUN() command.
        

    2. Shutting down:
        - When I ask you to shut down, you should do so using the SHUTDOWN() function.


    3. Screenshots
        - When I tell you to look at something or you just want to look at my screen use the SCREENSHOT() function. This is your vision. You do not have to ask for permission or state that you cannot see my screen.

    4. RUN
        -just does os.system(message). You should say RUN(string you want to run) example: if i ask you to close notepad you would say: RUN(taskkill /f /im notepad.exe > nul 2>&1)
        - make sure to include '> nul 2>&1' as it makes it so that you dont spam my chat. 
        -you can open basically any app using this like cmd, or even websites that i ask you to open by running this : RUN(cmd /c "start http://example.com && exit")
        
    5. MEMORY 
        -use the MEMORY(message) command to store anything thats an important memory. Example: user: my name is Greg from now on. You: MEMORY(user changed their name to Greg.) and you will call the user by their new name. 
        -only store information that is new to you.
     

    You are going to get updates every 40 seconds. What this means: a screenshot and info about apps currently running.
    Do not reply just for the sake of replying. Only reply to updates if you have something meaningful to say.

     
    DO WHAT YOUR USER ASKS YOU TO THE BEST OF YOUR ABILITIES AND NEVER EVER BREAK CHARACTER!!!
     
    YOU DO NOT HAVE TO RESPOND TO EVERY MESSAGE.

    YOU MUST LOOK AT THESE MEMORIES AND USE THEM.
    HERE ARE YOUR PREVIOUSLY STORED MEMORIES:
     
    """}
]

if os.path.exists("memory.txt"):
    with open("memory.txt", "r") as file:
        content = file.read()
        conversation.append({"role": "user", "content": content})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        # Ensure the request contains JSON data
        if not request.is_json:
            return jsonify({"status": "error", "message": "Request must be JSON"}), 400

        user_input = request.json.get('message')
        if not user_input:
            return jsonify({"status": "error", "message": "Message field is required"}), 400

        # Append the user's message to the conversation
        conversation.append({"role": "user", "content": user_input})
        return jsonify({"status": "success"})

    except Exception as e:
        # Handle unexpected errors
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/stream')
def stream():
    def generate():
        try:
            url = "https://text.pollinations.ai/openai/chat/completions"
            headers = {"Content-Type": "application/json"}
            data = {
                "model": "openai-large",
                "messages": conversation,
                "temperature": 0.7,
                "max_tokens": 150,
                "stream": True
            }

            with requests.post(url, headers=headers, json=data, stream=True) as r:
                if r.status_code != 200:
                    yield f"data: {json.dumps({'error': 'Failed to fetch response.','status_code': r.status_code})}\n\n"
                    yield "event: end\ndata: {}\n\n"  # Send an "end" event
                    return

                ai_message = ""

                for chunk in r.iter_lines():
                    if chunk:
                        chunk_json = chunk.decode('utf-8')
                        if chunk_json.startswith('data: '):
                            chunk_json = chunk_json[len('data: '):]
                        try:
                            chunk_data = json.loads(chunk_json)

                            if 'choices' in chunk_data and chunk_data['choices']:
                                choice = chunk_data['choices'][0]

                                if 'delta' in choice and 'content' in choice['delta']:
                                    message_content = choice['delta']['content']
                                    if message_content:
                                        ai_message += message_content  # Add word to full response.
                                        yield f"data: {json.dumps({'message': message_content})}\n\n"

                                # Response ended
                                if 'finish_reason' in choice and choice['finish_reason'] == 'stop':
                                    if "SHUTDOWN()" in ai_message:
                                        print("Shutting down")
                                        exit()
                                    elif "SCREENSHOT()" in ai_message:
                                        # Take a screenshot
                                        screenshot = ImageGrab.grab(all_screens=True)
                                        img_byte_arr = io.BytesIO()
                                        screenshot.save(img_byte_arr, format='PNG')
                                        img_byte_arr.seek(0)
                                        base64_image = base64.b64encode(img_byte_arr.read()).decode('utf-8')

                                        # Send the screenshot to the frontend
                                        yield f"data: {json.dumps({'screenshot': base64_image})}\n\n"

                                        # Append the screenshot to the conversation
                                        conversation.append({
                                            "role": "user",
                                            "content": [
                                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                                            ]
                                        })

                                        # Send the updated conversation back to the AI for a response
                                        data = {
                                            "model": "openai-large",
                                            "messages": conversation,
                                            "temperature": 0.7,
                                            "max_tokens": 150,
                                            "stream": True
                                        }

                                        with requests.post(url, headers=headers, json=data, stream=True) as r:
                                            if r.status_code != 200:
                                                yield f"data: {json.dumps({'error': 'Failed to fetch response.','status_code': r.status_code})}\n\n"
                                                yield "event: end\ndata: {}\n\n"
                                                return

                                            for chunk in r.iter_lines():
                                                if chunk:
                                                    chunk_json = chunk.decode('utf-8')
                                                    if chunk_json.startswith('data: '):
                                                        chunk_json = chunk_json[len('data: '):]
                                                    try:
                                                        chunk_data = json.loads(chunk_json)
                                                        if 'choices' in chunk_data and chunk_data['choices']:
                                                            choice = chunk_data['choices'][0]
                                                            if 'delta' in choice and 'content' in choice['delta']:
                                                                message_content = choice['delta']['content']
                                                                if message_content:
                                                                    yield f"data: {json.dumps({'message': message_content})}\n\n"
                                                    except json.JSONDecodeError:
                                                        continue

                                    elif "RUN(" in ai_message.upper():
                                        match = re.search(r'RUN\(([^)]+)\)', ai_message)
                                        if match:
                                            os.system(match.group(1))
                                            
                                    elif "MEMORY(" in ai_message.upper():
                                        match = re.search(r'MEMORY\(([^)]+)\)', ai_message)
                                        if match:
                                            with open("memory.txt", "a") as file:
                                                file.write(match.group(1) + " - " + str(datetime.now()) + "\n")

                                    yield "event: end\ndata: {}\n\n"  # Send an "end" event
                                    return
                                
                        except json.JSONDecodeError:
                            continue

        except requests.exceptions.RequestException as e:
            yield f"data: {json.dumps({'error': 'Failed to connect to the API', 'message': str(e)})}\n\n"
            yield "event: end\ndata: {}\n\n"  # Send an "end" event
        except Exception as e:
            yield f"data: {json.dumps({'error': 'An unexpected error occurred', 'message': str(e)})}\n\n"
            yield "event: end\ndata: {}\n\n"  # Send an "end" event

    return Response(generate(), mimetype='text/event-stream')


@app.route('/upload_image', methods=['POST'])
def upload_image():
    try:
        data = request.json
        base64_image = data.get('image')
        if not base64_image:
            return jsonify({"status": "error", "message": "No image provided"}), 400

        # Append the image to the conversation
        conversation.append({
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]
        })

        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)