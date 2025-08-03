import subprocess

class AndroidAdmin:
    def __init__(self, run_shell_command_func):
        self.run_shell_command = run_shell_command_func

    def list_android_packages(self):
        """Lists all installed Android packages using pm list packages."""
        return self.run_shell_command("pm list packages")

    def get_device_info(self):
        """Gathers comprehensive Android device information using getprop and termux-info."""
        device_info = {}
        device_info["termux_info"] = self.run_shell_command("termux-info")
        device_info["android_version"] = self.run_shell_command("getprop ro.build.version.release")
        device_info["device_model"] = self.run_shell_command("getprop ro.product.model")
        device_info["build_id"] = self.run_shell_command("getprop ro.build.id")
        return device_info

    def manage_app_permissions(self, package_name, permission, grant=True):
        """Grants or revokes an Android app permission using adb. Requires adb to be set up and device connected/rooted."""
        action = "grant" if grant else "revoke"
        return self.run_shell_command(f"adb shell pm {action} {package_name} {permission}")

    def clear_app_data(self, package_name):
        """Clears an Android application's data using adb. Requires adb to be set up and device connected/rooted."""
        return self.run_shell_command(f"adb shell pm clear {package_name}")

    def reboot_device(self):
        """Reboots the Android device using adb. Requires adb to be set up and device connected/rooted."""
        return self.run_shell_command("adb reboot")

    def shutdown_device(self):
        """Shuts down the Android device using adb. Requires adb to be set up and device connected/rooted."""
        return self.run_shell_command("adb shell reboot -p")

    def run_kali_command(self, command):
        """Executes a command within the Kali Linux environment using the KaliCLI alias."""
        return self.run_shell_command(f"proot-distro login debian -- {command}")

    def get_battery_status(self):
        """Gets the device's battery status using termux-battery-status."""
        return self.run_shell_command("termux-battery-status")

    def get_storage_info(self):
        """Gets the device's storage information using df -h."""
        return self.run_shell_command("df -h")

    def list_termux_services(self):
        """Lists all available Termux services and their status."""
        return self.run_shell_command("termux-service -l")

    def update_all_packages(self):
        """Updates all installed Termux packages using pkg upgrade."""
        return self.run_shell_command("pkg upgrade -y")

    def list_installed_packages(self):
        """Lists all installed Termux packages."""
        return self.run_shell_command("pkg list-installed")

    def listen_for_command(self):
        """Uses speech-to-text to listen for a voice command."""
        return self.run_shell_command("termux-speech-to-text")

    def send_notification(self, title, content):
        """Sends a notification to the Android device."""
        return self.run_shell_command(f'termux-notification --title "{title}" --content "{content}"')

    def vibrate(self, duration_ms=500):
        """Makes the device vibrate for a specified duration."""
        return self.run_shell_command(f"termux-vibrate -d {duration_ms}")

    def text_to_speech(self, text):
        """Uses text-to-speech to speak a message on the device."""
        return self.run_shell_command(f'termux-tts-speak "{text}"')
