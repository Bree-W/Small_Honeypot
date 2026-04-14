# Small_Honeypot
This is a honeypot I made with AI assistance for a class project, this will be a repo for any on-going improvements I make to it.

## 4/13/2026
The honeypot should be run in a seperate terminal than the attacker simply by running the python script. The honeypot then has the ability to be scanned via nmap, which will show telnet to be a vulnerable port. Then, the attacker is able to telnet into the system where there is a fake root directory and a fake flag. From the honeypot terminal, you are able to see every command the attacker runs. There are a few bugs, such as the attacker is unable to ^C out of the terminal once they have telneted into it, making them quite stuck in the honeypot (haha). Additionally, I would like to add more directories to make it as much like a fake computer as possible.
