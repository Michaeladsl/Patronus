# Patronus
Patronus was designed with penetration testers in mind! This dynamic tool captures command line inputs during security assessments, meticulously redacts any sensitive information, and organizes the data by command type. All the organized commands are then displayed through a user-friendly, interactive web interface, making it easy to review and manage. With Patronus, penetration testers can cast away the shadows of data mishandling and ensure a secure and streamlined workflow.

Ensure Asciinema is installed!!!!

## Usage

By default, patronus will run the redact, split, and server scripts.
```
python3 patronus.py
```


Configure your zsh environment for automatic recordings.
```
python3 patronus.py config
```


Patronus allows for individual running of tools
```
python3 patronus.py redact,split,server,config
```


## Recordings
The scripts look for the necessary files in the static directory when running. If configuring outside of using the 'config' option, make sure the full scritps are stored in static/full and create the static/redacted_full and the static/splits directories.
