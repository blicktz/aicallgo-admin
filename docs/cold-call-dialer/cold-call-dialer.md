Please create a sub application called "Cold Call Assistant" in the admin-board application, but it should live outside the of the main admin-board, with a totally separate entry page. The application should allow a user, such as a sales representative, to streamline their cold calling process.
Here is a detailed breakdown of the required functionality:
1. Contact Importing:
The initial view of the app should be a file upload interface.
Users must be able to upload a CSV file containing their contact list.
The CSV parser should expect the following header columns: name, company, phone (required), and title (optional).
The application should validate the CSV headers and display an error message if the required columns are missing.
Once parsed, the contacts should be displayed in a list, and the file upload interface should be hidden.
2. Contact List Display:
Display the imported contacts in a clean, readable table.
The table columns should include: Name/Title, Company, Phone Number, and Call Status.
Initially, the "Call Status" for all contacts should be "Not Called".
Each row in the table must have a "Dial" button.
There should be a "Load New List" button available to clear the current contact list and return to the file upload screen.
3. Web-Based Calling (Outcall agent Integration):
Clicking the "Dial" button for a contact should initiate an outbound phone call using the outcall agent, create new endpoint for this in outcall agent since existing endpoints are all for AI outcalling, we need now for human sales call
Before dialing, the app must request microphone permissions from the user.
The app should validate that the phone number is in the E.164 format (e.g., +15551234567) before attempting to dial.
To make calls, the frontend will need to use the interal api key to call direclty the outcall agent within the digital ocean vpc with internal url
4. Dialer Modal UI:
When a call is initiated, a modal overlay should appear, displaying the active call information.
This modal should manage and display the call's state:
"Dialing...": Shown while the connection is being established.
"Connected": Once the call connects, this state should display a running timer (e.g., 00:01, 00:02...).
The modal must provide in-call controls:
A prominent "End Call" button to hang up.
A "Mute/Unmute" button for the user's microphone.
The modal UI must make sure the user can use browser's mic and speaker to talk with the one they called over outcall agent in the browser 
5. Post-Call Logging:
When a call ends (either by hanging up or disconnection), the dialer modal should transition into a "Log Call" form.
This form must include:
A dropdown menu to select the call's Outcome (e.g., "Connected", "Left Voicemail", "No Answer", "Not Interested", "Follow Up").
A multi-line textarea for the user to enter Notes about the conversation.
The form should have "Save Log" and "Cancel" buttons.
Saving should update the corresponding contact in the main list with the selected outcome and notes, then close the modal.
Canceling should discard any notes and close the modal without updating the contact.
