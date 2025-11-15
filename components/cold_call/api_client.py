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
