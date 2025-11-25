"""API client for outcall-agent cold call endpoints."""
import os
import logging
from typing import Dict, Any, Optional
import httpx
from config.settings import settings

logger = logging.getLogger(__name__)


class ColdCallAPIClient:
    """HTTP client for outcall-agent cold call API."""

    def __init__(self):
        """Initialize the API client."""
        # Get outcall-agent URL from environment or settings
        self.base_url = os.getenv('OUTCALL_AGENT_INTERNAL_URL', 'http://outcall-agent:8000')
        self.api_key = os.getenv('INTERNAL_API_KEY', '')
        self.timeout = httpx.Timeout(30.0, connect=10.0)

        # Remove trailing slash
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]

        logger.info(f"ColdCallAPIClient initialized with base_url: {self.base_url}")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key."""
        return {
            'Content-Type': 'application/json',
            'X-API-Key': self.api_key,
        }

    async def initiate_call(self, to_phone: str, from_phone: Optional[str] = None) -> Dict[str, Any]:
        """Initiate a cold call.

        Args:
            to_phone: Destination phone number (E.164 format)
            from_phone: Caller ID phone number (E.164 format, optional)

        Returns:
            Conference details including SIDs and access token

        Raises:
            httpx.HTTPError: If API request fails

        Note:
            Provider is determined by TELEPHONY_SYSTEM environment variable on the server.
        """
        url = f"{self.base_url}/aicallgo/api/v1/cold-call/initiate"

        payload = {
            'to_phone': to_phone,
        }

        if from_phone:
            payload['from_phone'] = from_phone

        logger.info(f"Initiating cold call to {to_phone}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json=payload,
                headers=self._get_headers(),
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"Cold call initiated: conference_sid={data.get('conference_sid')}")
            return data

    async def join_webrtc(self, conference_id: str, client_id: str,
                         provider: str = 'twilio', sdp_offer: Optional[str] = None) -> Dict[str, Any]:
        """Join WebRTC participant to conference.

        Args:
            conference_id: Conference identifier
            client_id: Unique identifier for this WebRTC client
            provider: Telephony provider ('twilio' or 'telnyx')
            sdp_offer: Optional SDP offer from browser

        Returns:
            WebRTC connection details (access_token for Twilio, sip_username/password for Telnyx)

        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.base_url}/aicallgo/api/v1/cold-call/webrtc-join"

        payload = {
            'conference_id': conference_id,
            'client_id': client_id,
            'provider': provider,
        }

        if sdp_offer:
            payload['sdp_offer'] = sdp_offer

        logger.info(f"Joining WebRTC to conference {conference_id} with provider {provider}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json=payload,
                headers=self._get_headers(),
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"WebRTC joined: participant_sid={data.get('participant_sid')}")
            return data

    async def mute_participant(self, conference_sid: str, participant_sid: str,
                              muted: bool = True) -> Dict[str, Any]:
        """Mute or unmute a conference participant.

        Args:
            conference_sid: Conference SID
            participant_sid: Participant SID
            muted: True to mute, False to unmute

        Returns:
            Control action result

        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.base_url}/aicallgo/api/v1/cold-call/control/mute"

        payload = {
            'conference_sid': conference_sid,
            'participant_sid': participant_sid,
            'action': 'mute' if muted else 'unmute',
            'value': muted,
        }

        logger.info(f"{'Muting' if muted else 'Unmuting'} participant {participant_sid}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json=payload,
                headers=self._get_headers(),
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"Participant control successful: muted={data.get('muted')}")
            return data

    async def end_call(self, conference_sid: str) -> Dict[str, Any]:
        """End a conference and hang up all participants.

        Args:
            conference_sid: Conference SID

        Returns:
            Conference termination result

        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.base_url}/aicallgo/api/v1/cold-call/end"

        payload = {
            'conference_sid': conference_sid,
        }

        logger.info(f"Ending conference {conference_sid}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json=payload,
                headers=self._get_headers(),
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"Conference ended: status={data.get('status')}")
            return data

    async def get_status(self, conference_sid: str) -> Dict[str, Any]:
        """Get conference status.

        Args:
            conference_sid: Conference SID or friendly name

        Returns:
            Conference status details

        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.base_url}/aicallgo/api/v1/cold-call/status/{conference_sid}"

        logger.info(f"[STATUS REQUEST] URL: {url}")
        logger.info(f"[STATUS REQUEST] Conference SID: {conference_sid}")
        logger.info(f"[STATUS REQUEST] Base URL: {self.base_url}")
        logger.info(f"[STATUS REQUEST] API Key present: {bool(self.api_key)}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                )
                logger.info(f"[STATUS RESPONSE] Status Code: {response.status_code}")
                response.raise_for_status()

                data = response.json()
                logger.info(f"[STATUS SUCCESS] Conference status: status={data.get('status')}, participants={data.get('participant_count')}")
                return data
            except httpx.HTTPError as e:
                logger.error(f"[STATUS ERROR] HTTP Error: {e}")
                logger.error(f"[STATUS ERROR] Response: {getattr(e, 'response', None)}")
                raise

    def initiate_call_sync(self, to_phone: str, from_phone: Optional[str] = None) -> Dict[str, Any]:
        """Synchronous version of initiate_call."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.initiate_call(to_phone, from_phone))

    def join_webrtc_sync(self, conference_id: str, client_id: str,
                        provider: str = 'twilio', sdp_offer: Optional[str] = None) -> Dict[str, Any]:
        """Synchronous version of join_webrtc."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.join_webrtc(conference_id, client_id, provider, sdp_offer))

    def mute_participant_sync(self, conference_sid: str, participant_sid: str,
                             muted: bool = True) -> Dict[str, Any]:
        """Synchronous version of mute_participant."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.mute_participant(conference_sid, participant_sid, muted))

    def end_call_sync(self, conference_sid: str) -> Dict[str, Any]:
        """Synchronous version of end_call."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.end_call(conference_sid))

    def get_status_sync(self, conference_sid: str) -> Dict[str, Any]:
        """Synchronous version of get_status."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.get_status(conference_sid))

    # ============================================================================
    # Audio Playback Methods (Twilio-only feature)
    # ============================================================================

    async def get_audio_files(self) -> list[Dict[str, Any]]:
        """Get available audio files for playback.

        Returns:
            List of audio file information dicts

        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.base_url}/aicallgo/api/v1/cold-call/audio-files"

        logger.info("Fetching audio files")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                url,
                headers=self._get_headers(),
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"Audio files retrieved: {len(data)} files")
            return data

    async def control_audio_playback(
        self,
        conference_sid: str,
        audio_id: str,
        action: str,
    ) -> Dict[str, Any]:
        """Control audio playback in conference.

        Args:
            conference_sid: Conference SID
            audio_id: Audio file ID to play
            action: Action to perform ('play' or 'stop')

        Returns:
            Audio playback control result

        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.base_url}/aicallgo/api/v1/cold-call/control/audio-playback"

        payload = {
            'conference_sid': conference_sid,
            'audio_id': audio_id,
            'action': action,
        }

        logger.info(f"Controlling audio playback: {action} {audio_id} in {conference_sid}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json=payload,
                headers=self._get_headers(),
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"Audio playback control successful: {data.get('message')}")
            return data

    def get_audio_files_sync(self) -> list[Dict[str, Any]]:
        """Synchronous version of get_audio_files."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.get_audio_files())

    def control_audio_playback_sync(
        self,
        conference_sid: str,
        audio_id: str,
        action: str,
    ) -> Dict[str, Any]:
        """Synchronous version of control_audio_playback."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.control_audio_playback(conference_sid, audio_id, action)
        )

    async def add_audio_player(self, conference_sid: str) -> Dict[str, Any]:
        """Add audio player participant to conference.

        This endpoint adds a TwiML App participant that enables bidirectional
        audio streaming for audio playback in Twilio conferences. Must be called
        after conference creation, before using audio playback controls.

        Args:
            conference_sid: Conference SID to add audio player to

        Returns:
            Result dict with success status, conference_sid, call_sid, and message

        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.base_url}/aicallgo/api/v1/cold-call/add-audio-player/{conference_sid}"

        logger.info(f"Adding audio player participant to conference {conference_sid}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                headers=self._get_headers(),
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"Audio player added: call_sid={data.get('call_sid')}")
            return data

    def add_audio_player_sync(self, conference_sid: str) -> Dict[str, Any]:
        """Synchronous version of add_audio_player."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.add_audio_player(conference_sid))

    def add_audio_player_with_retry_sync(
        self,
        conference_sid: str,
        max_attempts: int = 10,
        delay_ms: int = 500,
    ) -> Dict[str, Any]:
        """Add audio player participant with retry logic.

        Retries if conference not found (may still be initializing).
        Conference creation happens asynchronously when browser joins,
        so we need to poll until it's ready.

        Args:
            conference_sid: Conference SID to add audio player to
            max_attempts: Maximum retry attempts (default: 10)
            delay_ms: Delay between retries in milliseconds (default: 500)

        Returns:
            Result dict from successful add_audio_player call

        Raises:
            httpx.HTTPError: If all retries fail
        """
        import time

        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                # Try to add audio player
                result = self.add_audio_player_sync(conference_sid)
                logger.info(f"Audio player added successfully on attempt {attempt}")
                return result

            except httpx.HTTPStatusError as e:
                last_error = e

                # Only retry on 404 (conference not found)
                if e.response.status_code == 404:
                    if attempt < max_attempts:
                        logger.info(
                            f"Conference not ready, retrying in {delay_ms}ms "
                            f"(attempt {attempt}/{max_attempts})"
                        )
                        time.sleep(delay_ms / 1000.0)
                        continue
                    else:
                        logger.error(
                            f"Conference not ready after {max_attempts} attempts"
                        )
                else:
                    # Other HTTP errors - don't retry
                    logger.error(f"HTTP error {e.response.status_code}, not retrying")
                    raise

            except Exception as e:
                # Network errors or other issues - retry
                last_error = e
                if attempt < max_attempts:
                    logger.warning(f"Error on attempt {attempt}: {str(e)}, retrying...")
                    time.sleep(delay_ms / 1000.0)
                    continue
                else:
                    logger.error(f"Failed after {max_attempts} attempts: {str(e)}")

        # All retries exhausted
        raise last_error or Exception("Failed to add audio player after retries")

    # ============================================================================
    # Direct Calling Methods (Telnyx WebRTC Direct Mode)
    # ============================================================================

    async def get_direct_webrtc_credentials(self) -> Dict[str, Any]:
        """Get SIP credentials for Telnyx WebRTC direct calling.

        Returns:
            SIP username and password for WebRTC authentication

        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.base_url}/aicallgo/api/v1/cold-call/direct/webrtc-credentials"

        logger.info("Getting direct WebRTC credentials")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                url,
                headers=self._get_headers(),
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"Direct WebRTC credentials retrieved: mode={data.get('mode')}")
            return data

    async def start_direct_recording(
        self,
        call_control_id: str,
        to_phone: str,
        from_phone: str
    ) -> Dict[str, Any]:
        """Start recording for a direct WebRTC call.

        Args:
            call_control_id: Call control ID from Telnyx WebRTC SDK
            to_phone: Destination phone number
            from_phone: Caller ID

        Returns:
            Recording start confirmation

        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.base_url}/aicallgo/api/v1/cold-call/direct/start-recording"

        payload = {
            'call_control_id': call_control_id,
            'to_phone': to_phone,
            'from_phone': from_phone,
        }

        logger.info(f"Starting recording for direct call: {call_control_id}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json=payload,
                headers=self._get_headers(),
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"Direct call recording started: {call_control_id}")
            return data

    def get_direct_webrtc_credentials_sync(self) -> Dict[str, Any]:
        """Synchronous version of get_direct_webrtc_credentials."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.get_direct_webrtc_credentials())

    def start_direct_recording_sync(
        self,
        call_control_id: str,
        to_phone: str,
        from_phone: str
    ) -> Dict[str, Any]:
        """Synchronous version of start_direct_recording."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.start_direct_recording(call_control_id, to_phone, from_phone)
        )

    async def register_direct_call(
        self,
        call_id: str,
        to_phone: str,
        from_phone: str
    ) -> Dict[str, Any]:
        """Register a direct call before browser initiates it.

        Args:
            call_id: Unique identifier generated by frontend
            to_phone: Destination phone number
            from_phone: Caller ID

        Returns:
            Registration confirmation

        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.base_url}/aicallgo/api/v1/cold-call/direct/register-call"

        payload = {
            'call_id': call_id,
            'to_phone': to_phone,
            'from_phone': from_phone,
        }

        logger.info(f"Registering direct call: {call_id}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json=payload,
                headers=self._get_headers(),
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"Direct call registered: {call_id}")
            return data

    async def hangup_direct_call(self, call_id: str) -> Dict[str, Any]:
        """Hangup a Telnyx direct call.

        Args:
            call_id: Call identifier used by frontend

        Returns:
            Hangup confirmation

        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.base_url}/aicallgo/api/v1/cold-call/direct/hangup"

        payload = {'call_id': call_id}

        logger.info(f"Hanging up direct call: {call_id}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json=payload,
                headers=self._get_headers(),
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"Direct call hangup initiated: {call_id}")
            return data

    def register_direct_call_sync(
        self,
        call_id: str,
        to_phone: str,
        from_phone: str
    ) -> Dict[str, Any]:
        """Synchronous version of register_direct_call."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.register_direct_call(call_id, to_phone, from_phone)
        )

    def hangup_direct_call_sync(self, call_id: str) -> Dict[str, Any]:
        """Synchronous version of hangup_direct_call."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.hangup_direct_call(call_id))
