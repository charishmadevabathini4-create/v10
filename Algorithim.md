step 1 : Receive the user's text from the website user interface and send it to the Flask backend.

step 2 : Send the user's text from the Flask backend to the Gemini API for initial analysis.

step 3 : Receive the analyzed information from the Gemini API as the output.

step 4 : Create a PyTorch model in the backend that matches the Gemini API output with the dataset stored in `Preliminary_data.db` using SQLite3, where the dataset contains psychological trauma, behaviors, symptoms of psychological disorders, patterns, emotional distress, signs, and anxiety-related information.

step 5 : Generate the matched output from the PyTorch model in the format: "A person aged __ is suffering from __ due to the series of events: __", where the age, matched condition, and series of events are obtained from the available user information and model output.

step 6 : Send the structured output from the PyTorch model to the Gemini 2.5 Flash API and request a further in-depth assessment of the identified condition and possible methods to overcome or manage the problem.

step 7 : Receive the output from the Gemini 2.5 Flash API and display the recommended methods, ways, and guidance to overcome or manage the identified problem to the user in a detailed and easy-to-understand format.

step 8   : Record the user's input, PyTorch model output, Gemini 2.5 Flash input, and Gemini 2.5 Flash output in a structured report format and store the report in `Secondary_data.db` using SQLite3.

step 9 : If the identified problem is severe, use the user's location and the psychologist information stored in `Third_data.db` to identify the nearest suitable psychologist.

step 10   : Use the Gemini API to determine the nearest psychologist location based on the user's location and the psychologist locations available in `Third_data.db`.

step 11 : Fetch the selected psychologist's name, email address, phone number, and location from `Third_data.db`.

step 12 : Send the generated report to the selected psychologist through email.

step 13  : Along with the report, send the psychologist a link to a website where the psychologist can accept the request and provide the available appointment date and time slots.

step 14   : Receive the psychologist's confirmation and selected appointment slot through the appointment website.

step 15 : Once the psychologist confirms the request, send the user an email containing the psychologist's name, location, contact details, confirmed appointment date, and confirmed appointment time slot.
