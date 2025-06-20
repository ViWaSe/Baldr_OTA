# OTA-Update-Config-Migration tool
# Updates the existing config.json with new objects if there is a difference

# ! NOT TESTED YET - Do not release Baldr6.4 until this is done!

version = "0.1.0"
config_target_version = "5.5"

import ujson as json
import os
from logger import Log

class OTA_Diff_Migrator:
    def __init__(
            self, 
            config_file, 
            schema_diff, 
            version_key="Version", 
            target_version=None
            ):
        self.config_file = config_file
        self.schema_diff = schema_diff
        self.version_key = version_key
        self.target_version = target_version

    def run(self):
        config = self._load_config()
        current_version = config.get(self.version_key, None)
        if self.target_version is not None:
            if current_version == self.target_version:
                return
            Log('OTA', f'[ INFO  ]: Migration from {current_version} to {self.target_version}')

        changed = self._apply_diff(config, self.schema_diff)
        if changed:
            config[self.version_key] = self.target_version if self.target_version is not None else current_version
            self._safe_write(config)
            Log('OTA', '[ INFO  ]: JSON-File updated')
        else:
            Log('OTA', '[ INFO  ]:Migration not necessary, no new objects in json!')

    def _load_config(self):
        try:
            with open(self.config_file) as f:
                return json.load(f)
        except Exception as e:
            Log('OTA', f'[ FAIL  ]: Config file not dound or corrupt!')
            return {}

    def _apply_diff(self, target, diff):
        changed = False
        for key, value in diff.items():
            if key == "*":
                if isinstance(target, list):
                    for item in target:
                        if isinstance(item, dict):
                            if self._apply_diff(item, value):
                                changed = True
                else:
                    Log('OTA', f'[ WARN  ]: Wildcard * only allowed for list objects!')
            elif isinstance(value, dict):
                if key not in target or not isinstance(target[key], (dict, list)):
                    target[key] = {} if isinstance(value, dict) else value
                    changed = True
                if self._apply_diff(target[key], value):
                    changed = True
            else:
                if key not in target:
                    target[key] = value
                    changed = True
        return changed

    def _safe_write(self, config):
        tmp_file = self.config_file + ".tmp"
        backup_file = self.config_file + ".bak"
        try:
            with open(tmp_file, "w") as f:
                json.dump(config, f)
            if os.path.exists(self.config_file):
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                os.rename(self.config_file, backup_file)
            os.rename(tmp_file, self.config_file)
        except Exception as e:
            Log('OTA', f'[ FAIL  ]: Error while writing config: {e}. Restoring backup...')
            self.restore_backup()

    def restore_backup(self):
        backup_file = self.config_file + ".bak"
        if os.path.exists(backup_file):
            os.rename(backup_file, self.config_file)
            Log('OTA', f'[ INFO  ]: Backup restored.')
        else:
            Log('OTA', f'[ FAIL  ]: No Backup found.')

# =====================================================================================================================
# New JSON-Objects:
SCHEMA_DIFF = {
    "MQTT-config": {
        "*": {
            "publish_in_json": False
        }
    }
}

# set up migration
migrator = OTA_Diff_Migrator("/params/config.json", SCHEMA_DIFF, target_version=config_target_version)
migrator.run()
# =====================================================================================================================