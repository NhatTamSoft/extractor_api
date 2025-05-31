import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

def ask_gemini(prompt: str, model_name: str = "gemini-2.0-flash") -> str:
    """
    Gửi một yêu cầu đến API Gemini bằng thư viện chính thức và trả về phản hồi văn bản.

    Parameters:
    - prompt (str): The prompt to send to the Gemini model.
    - model_name (str): The name of the Gemini model to use (defaults to "gemini-2.0-flash").

    Returns:
    - str: The text response from the Gemini model, or an error message if something goes wrong.
    """
    try:
        # Kiểm tra và cấu hình API key
        api_key = os.getenv('GOOGLE_API_KEY') #"AIzaSyDQaVqocOL27eZkJq6kGB_WzDXer6KrceI"
        
        genai.configure(api_key=api_key)

        # Initialize the GenerativeModel
        model = genai.GenerativeModel(model_name)

        # Generate content
        response = model.generate_content(prompt)

        # Access the text from the response
        if response.candidates and response.candidates[0].content.parts:
            text_response = response.candidates[0].content.parts[0].text
            return text_response
        else:
            return f"Error: Unexpected response structure or no content. Full response: {response}"

    except Exception as e:
        # Catch any exceptions from the API call or processing
        return f"An error occurred: {e}"

# Example usage of the ask_gemini function
if __name__ == "__main__":
    print("Calling Gemini Flash model...")
    response_flash = ask_gemini("""Xin chào""")
    print(f"\nResponse from Gemini Flash:\n{response_flash}")
