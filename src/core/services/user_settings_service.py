# user_settings_service.py
import json
import logging
from datetime import UTC, datetime
from typing import Any

from flask import current_app, has_app_context

from src.infrastructure.database import UserSettings, db

logger = logging.getLogger(__name__)

class UserSettingsService:
    """
    Service for managing user settings with database persistence.
    Handles universe selections, filters, and other user preferences.
    """

    def __init__(self, cache_control=None, app=None):
        """
        Initialize the user settings service.
        
        Args:
            cache_control: CacheControl instance for universe validation
            app: Flask application instance for context management
        """
        self.cache_control = cache_control
        self.app = app
        logger.debug("UserSettingsService initialized")

    def _ensure_app_context(self):
        """Ensure we have Flask app context for database operations."""
        if has_app_context():
            return None

        if self.app is None:
            # Try to get app from current_app
            try:
                self.app = current_app._get_current_object()
            except RuntimeError:
                logger.error("No Flask app available for context creation")
                raise RuntimeError("UserSettingsService requires Flask app for database operations")

        # Push app context
        return self.app.app_context()

    def get_universe_selections(self, user_id: int) -> dict[str, list[str]]:
        """
        Get user's universe selections from src.infrastructure.database with fallback to defaults.
        
        Args:
            user_id: User ID
            
        Returns:
            dict: Universe selections for each tracker type
        """
        try:
            # Handle app context
            context_manager = self._ensure_app_context()
            if context_manager:
                with context_manager:
                    return self._get_universe_selections_with_context(user_id)
            else:
                return self._get_universe_selections_with_context(user_id)

        except Exception as e:
            logger.error(f"Error getting universe selections for user {user_id}: {e}", exc_info=True)
            # Return safe defaults on error
            return {
                'market': ['DEFAULT_UNIVERSE'],
                'highlow': ['DEFAULT_UNIVERSE']
            }

    def _get_universe_selections_with_context(self, user_id: int) -> dict[str, list[str]]:
        """Internal method that requires app context."""
        # Query database for universe selections
        setting = UserSettings.query.filter_by(
            user_id=user_id,
            key='universe_selections'
        ).first()

        if setting and setting.value:
            universe_selections = setting.value

            # Validate the structure
            if isinstance(universe_selections, dict):
                # Ensure both trackers have selections
                selections = {
                    'market': universe_selections.get('market', ['DEFAULT_UNIVERSE']),
                    'highlow': universe_selections.get('highlow', ['DEFAULT_UNIVERSE'])
                }

                # Validate universes exist
                selections = self._validate_universe_selections(selections)

                logger.debug(f"Retrieved universe selections for user {user_id}: {selections}")
                return selections

        # No setting found or invalid - return defaults
        default_selections = {
            'market': ['DEFAULT_UNIVERSE'],
            'highlow': ['DEFAULT_UNIVERSE']
        }

        logger.info(f"Using default universe selections for user {user_id}")
        return default_selections

    def save_universe_selections(self, user_id: int, selections: dict[str, list[str]]) -> bool:
        """
        Save universe selections to database.
        
        Args:
            user_id: User ID
            selections: Universe selections to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            context_manager = self._ensure_app_context()
            if context_manager:
                with context_manager:
                    return self._save_universe_selections_with_context(user_id, selections)
            else:
                return self._save_universe_selections_with_context(user_id, selections)

        except Exception as e:
            logger.error(f"Error saving universe selections for user {user_id}: {e}", exc_info=True)
            return False

    def _save_universe_selections_with_context(self, user_id: int, selections: dict[str, list[str]]) -> bool:
        """Internal save method that requires app context."""
        # Validate selections first
        validated_selections = self._validate_universe_selections(selections)

        # Prepare the value to store
        value_to_store = {
            'market': validated_selections.get('market', ['DEFAULT_UNIVERSE']),
            'highlow': validated_selections.get('highlow', ['DEFAULT_UNIVERSE']),
            'last_updated': datetime.now(UTC).isoformat(),
            'version': '1.0'
        }

        # Check if setting already exists
        existing_setting = UserSettings.query.filter_by(
            user_id=user_id,
            key='universe_selections'
        ).first()

        if existing_setting:
            # Update existing setting
            existing_setting.value = value_to_store
            existing_setting.updated_at = datetime.utcnow()
            logger.debug(f"Updated existing universe selections for user {user_id}")
        else:
            # Create new setting
            new_setting = UserSettings(
                user_id=user_id,
                key='universe_selections',
                value=value_to_store
            )
            db.session.add(new_setting)
            logger.debug(f"Created new universe selections for user {user_id}")

        db.session.commit()

        logger.info(f"Successfully saved universe selections for user {user_id}: {validated_selections}")
        return True


    def get_user_universe_selections(self, user_id: int) -> dict[str, list[str]]:
        """
        Wrapper method for UserUniverseManager compatibility.
        Get user's universe selections from src.infrastructure.database.
        
        Args:
            user_id: User ID to get selections for
            
        Returns:
            Dict with 'market' and 'highlow' universe lists
        """
        return self.get_universe_selections(user_id)

    def save_universe_selection(self, user_id: int, tracker_type: str, universes: list[str]) -> bool:
        """
        Wrapper method for UserUniverseManager compatibility.
        Save universe selection for a specific tracker type.
        
        Args:
            user_id: User ID
            tracker_type: 'market' or 'highlow'
            universes: List of universe names
            
        Returns:
            bool: True if save successful
        """
        try:
            # Get current selections
            current_selections = self.get_universe_selections(user_id)

            # Update the specific tracker type
            current_selections[tracker_type] = universes

            # Save all selections
            return self.save_universe_selections(user_id, current_selections)

        except Exception as e:
            logger.error(f"Error in save_universe_selection wrapper: {e}")
            return False

    def migrate_session_to_database(self, user_id: int, session_data: dict[str, Any]) -> bool:
        """
        One-time migration from session-based storage to database.
        
        Args:
            user_id: User ID
            session_data: Session data to migrate
            
        Returns:
            bool: True if migration successful, False otherwise
        """
        try:
            # Check if user already has database settings
            existing_setting = UserSettings.query.filter_by(
                user_id=user_id,
                key='universe_selections'
            ).first()

            if existing_setting:
                logger.debug(f"User {user_id} already has database settings, skipping migration")
                return True

            # Extract universe selections from session
            universe_selections = session_data.get('universe_selections', {})

            if universe_selections:
                # Migrate session data to database
                success = self.save_universe_selections(user_id, universe_selections)

                if success:
                    logger.info(f"Successfully migrated session data to database for user {user_id}")
                    return True
                logger.error(f"Failed to migrate session data for user {user_id}")
                return False
            # No session data to migrate - create defaults
            default_selections = {
                'market': ['DEFAULT_UNIVERSE'],
                'highlow': ['DEFAULT_UNIVERSE']
            }

            success = self.save_universe_selections(user_id, default_selections)

            if success:
                logger.info(f"Created default universe selections for user {user_id}")
                return True

        except Exception as e:
            logger.error(f"Error migrating session data for user {user_id}: {e}", exc_info=True)
            return False

    def get_user_setting(self, user_id: int, key: str, default: Any = None) -> Any:
        """
        Generic user setting getter with context handling.
        
        Args:
            user_id: User ID
            key: Setting key
            default: Default value if not found
            
        Returns:
            Setting value or default
        """
        try:
            context_manager = self._ensure_app_context()
            if context_manager:
                with context_manager:
                    return self._get_user_setting_with_context(user_id, key, default)
            else:
                return self._get_user_setting_with_context(user_id, key, default)

        except Exception as e:
            logger.error(f"Error getting setting {key} for user {user_id}: {e}", exc_info=True)
            return default

    def _get_user_setting_with_context(self, user_id: int, key: str, default: Any = None) -> Any:
        """Internal getter that requires app context."""
        setting = UserSettings.query.filter_by(
            user_id=user_id,
            key=key
        ).first()

        if setting and setting.value is not None:
            logger.debug(f"Retrieved setting {key} for user {user_id}")
            return setting.value

        logger.debug(f"Setting {key} not found for user {user_id}, returning default")
        return default

    def set_user_setting(self, user_id: int, key: str, value: Any) -> bool:
        """
        Generic user setting setter with context handling.
        
        Args:
            user_id: User ID
            key: Setting key
            value: Setting value
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            context_manager = self._ensure_app_context()
            if context_manager:
                with context_manager:
                    return self._set_user_setting_with_context(user_id, key, value)
            else:
                return self._set_user_setting_with_context(user_id, key, value)

        except Exception as e:
            logger.error(f"Error saving setting {key} for user {user_id}: {e}", exc_info=True)
            return False

    def _set_user_setting_with_context(self, user_id: int, key: str, value: Any) -> bool:
        """Internal setter that requires app context."""
        # Check if setting already exists
        existing_setting = UserSettings.query.filter_by(
            user_id=user_id,
            key=key
        ).first()

        if existing_setting:
            # Update existing setting
            existing_setting.value = value
            existing_setting.updated_at = datetime.utcnow()
            logger.debug(f"Updated setting {key} for user {user_id}")
        else:
            # Create new setting
            new_setting = UserSettings(
                user_id=user_id,
                key=key,
                value=value
            )
            db.session.add(new_setting)
            logger.debug(f"Created setting {key} for user {user_id}")

        db.session.commit()

        logger.info(f"Successfully saved setting {key} for user {user_id}")
        return True

    def _validate_universe_selections(self, selections: dict[str, list[str]]) -> dict[str, list[str]]:
        """
        Validate universe selections against available universes.
        
        Args:
            selections: Universe selections to validate
            
        Returns:
            dict: Validated selections with invalid universes removed
        """
        try:
            if not self.cache_control:
                logger.warning("No cache_control available for universe validation")
                return selections

            available_universes = self.cache_control.get_available_universes()

            validated = {}

            for tracker_type, universes in selections.items():
                if tracker_type not in ['market', 'highlow']:
                    logger.warning(f"Invalid tracker type: {tracker_type}")
                    continue

                valid_universes = []

                for universe_key in universes:
                    if universe_key in available_universes:
                        valid_universes.append(universe_key)
                    else:
                        logger.warning(f"Invalid universe key removed: {universe_key}")

                # Ensure at least one universe is selected
                if not valid_universes:
                    valid_universes = ['DEFAULT_UNIVERSE']
                    logger.info(f"No valid universes for {tracker_type}, using DEFAULT_UNIVERSE")

                validated[tracker_type] = valid_universes

            # Ensure both tracker types are present
            if 'market' not in validated:
                validated['market'] = ['DEFAULT_UNIVERSE']
            if 'highlow' not in validated:
                validated['highlow'] = ['DEFAULT_UNIVERSE']

            return validated

        except Exception as e:
            logger.error(f"Error validating universe selections: {e}", exc_info=True)
            # Return safe defaults on validation error
            return {
                'market': ['DEFAULT_UNIVERSE'],
                'highlow': ['DEFAULT_UNIVERSE']
            }

    def get_all_user_settings(self, user_id: int) -> dict[str, Any]:
        """
        Get all settings for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            dict: All user settings
        """
        try:
            settings = UserSettings.query.filter_by(user_id=user_id).all()

            result = {}
            for setting in settings:
                result[setting.key] = setting.value

            logger.debug(f"Retrieved {len(result)} settings for user {user_id}")
            return result

        except Exception as e:
            logger.error(f"Error getting all settings for user {user_id}: {e}", exc_info=True)
            return {}

    def delete_user_setting(self, user_id: int, key: str) -> bool:
        """
        Delete a user setting.
        
        Args:
            user_id: User ID
            key: Setting key to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            setting = UserSettings.query.filter_by(
                user_id=user_id,
                key=key
            ).first()

            if setting:
                db.session.delete(setting)
                db.session.commit()
                logger.info(f"Deleted setting {key} for user {user_id}")
                return True
            logger.debug(f"Setting {key} not found for user {user_id}")
            return True  # Consider it successful if it doesn't exist

        except Exception as e:
            logger.error(f"Error deleting setting {key} for user {user_id}: {e}", exc_info=True)
            db.session.rollback()
            return False

    def get_user_settings(self, user_id: int) -> dict[str, Any]:
        """
        Get all user settings for a given user ID.
        
        Args:
            user_id: User ID to get settings for
            
        Returns:
            Dict containing all user settings
        """
        try:
            user_settings = UserSettings.query.filter_by(user_id=user_id).all()
            settings_dict = {}

            for setting in user_settings:
                try:
                    # Try to parse as JSON, fall back to string
                    settings_dict[setting.key] = json.loads(setting.value) if setting.value else None
                except (json.JSONDecodeError, TypeError):
                    settings_dict[setting.key] = setting.value

            logger.debug(f"Retrieved {len(settings_dict)} settings for user {user_id}")
            return settings_dict

        except Exception as e:
            logger.error(f"Failed to get user settings for user {user_id}: {e}")
            return {}

    def get_all_user_watchlists(self) -> dict[str, list[str]]:
        """
        Get all user watchlists for caching in MarketDataSubscriber.
        
        Returns:
            Dict[user_id, symbols]: Map of user_id to list of watchlist symbols
        """
        try:
            context_manager = self._ensure_app_context()
            if context_manager:
                with context_manager:
                    return self._get_all_user_watchlists_with_context()
            else:
                return self._get_all_user_watchlists_with_context()

        except Exception as e:
            logger.error(f"Error getting all user watchlists: {e}", exc_info=True)
            return {}

    def _get_all_user_watchlists_with_context(self) -> dict[str, list[str]]:
        """Internal method to get all user watchlists - requires app context."""
        try:
            # Query all watchlist settings
            watchlist_settings = UserSettings.query.filter_by(key='watchlist').all()

            result = {}
            for setting in watchlist_settings:
                if setting.value:
                    try:
                        # Parse watchlist JSON
                        if isinstance(setting.value, list):
                            # Already a list
                            symbols = setting.value
                        elif isinstance(setting.value, str):
                            # Parse JSON string
                            symbols = json.loads(setting.value)
                        else:
                            # Try direct access
                            symbols = setting.value

                        # Validate symbols list
                        if isinstance(symbols, list) and all(isinstance(s, str) for s in symbols):
                            if symbols:  # Only cache non-empty watchlists
                                result[str(setting.user_id)] = symbols
                        else:
                            logger.warning(f"Invalid watchlist format for user {setting.user_id}: {type(symbols)}")

                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to parse watchlist for user {setting.user_id}: {e}")
                        continue

            logger.debug(f"Retrieved watchlists for {len(result)} users")
            return result

        except Exception as e:
            logger.error(f"Error in _get_all_user_watchlists_with_context: {e}", exc_info=True)
            return {}

    def get_user_watchlist(self, user_id: int) -> list[str]:
        """
        Get user's watchlist symbols.
        
        Args:
            user_id: User ID
            
        Returns:
            List of symbol strings
        """
        try:
            watchlist_data = self.get_user_setting(user_id, 'watchlist', [])

            # Ensure it's a list of strings
            if isinstance(watchlist_data, list):
                return [str(symbol) for symbol in watchlist_data if symbol]
            logger.warning(f"Invalid watchlist format for user {user_id}: {type(watchlist_data)}")
            return []

        except Exception as e:
            logger.error(f"Error getting watchlist for user {user_id}: {e}")
            return []

    def add_to_watchlist(self, user_id: int, symbol: str) -> bool:
        """
        Add symbol to user's watchlist.
        
        Args:
            user_id: User ID
            symbol: Symbol to add
            
        Returns:
            bool: True if successful
        """
        try:
            current_watchlist = self.get_user_watchlist(user_id)

            # Add symbol if not already present
            symbol = symbol.upper()
            if symbol not in current_watchlist:
                current_watchlist.append(symbol)
                return self.set_user_setting(user_id, 'watchlist', current_watchlist)

            return True  # Already in watchlist

        except Exception as e:
            logger.error(f"Error adding {symbol} to watchlist for user {user_id}: {e}")
            return False

    def remove_from_watchlist(self, user_id: int, symbol: str) -> bool:
        """
        Remove symbol from user's watchlist.
        
        Args:
            user_id: User ID
            symbol: Symbol to remove
            
        Returns:
            bool: True if successful
        """
        try:
            current_watchlist = self.get_user_watchlist(user_id)

            # Remove symbol if present
            symbol = symbol.upper()
            if symbol in current_watchlist:
                current_watchlist.remove(symbol)
                return self.set_user_setting(user_id, 'watchlist', current_watchlist)

            return True  # Not in watchlist

        except Exception as e:
            logger.error(f"Error removing {symbol} from watchlist for user {user_id}: {e}")
            return False
