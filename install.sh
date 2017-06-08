#!/bin/bash

echo "Installing Timesheeter on $HOST for user $USER..."

# Create starting script.
echo "Creating starting script..."

echo "Please add the path to the virtualenv folder if you use it!"

read venv_path

echo "#!/bin/bash" > timesheeter.sh
echo "" >> timesheeter.sh
if [ -n "$venv_path" ]
then
    echo "source $venv_path/bin/activate" >> timesheeter.sh
fi
echo "python3 timesheeter.py" >> timesheeter.sh

# Add execute permission to the script.
chmod +x timesheeter.sh

echo "Execute permission is set now."
echo "If you want to run Timesheeter from anywhere just create a symbolic link. e.g.: under at ~/.local/bin"
echo "Thanks for using Timesheeter. <3"