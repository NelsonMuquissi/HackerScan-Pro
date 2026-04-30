import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            # Rejeita conexão se não estiver autenticado
            await self.accept() # Aceita primeiro para poder mandar erro
            await self.send(text_data=json.dumps({"error": "Unauthorized"}))
            await self.close()
            return

        self.user_group = f"user_{self.user.id}_notifications"
        self.workspace_groups = []

        # Join user group
        await self.channel_layer.group_add(
            self.user_group,
            self.channel_name
        )

        # Join workspace groups
        workspaces = await self.get_user_workspaces()
        for ws_id in workspaces:
            group_name = f"workspace_{ws_id}"
            await self.channel_layer.group_add(group_name, self.channel_name)
            self.workspace_groups.append(group_name)

        await self.accept()

    @database_sync_to_async
    def get_user_workspaces(self):
        from users.models import WorkspaceMember, Workspace, UserRole
        if self.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            return list(Workspace.objects.filter(is_active=True).values_list("id", flat=True))
        return list(WorkspaceMember.objects.filter(user=self.user).values_list("workspace_id", flat=True))

    async def disconnect(self, close_code):
        # Leave user group
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(
                self.user_group,
                self.channel_name
            )
        
        # Leave workspace groups
        if hasattr(self, "workspace_groups"):
            for group_name in self.workspace_groups:
                await self.channel_layer.group_discard(
                    group_name,
                    self.channel_name
                )

    # Receive message from room group
    async def notification_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event["data"]))

    async def scan_update(self, event):
        """Handler for 'scan_update' events."""
        await self.send(text_data=json.dumps({
            "type": "scan_update",
            "payload": event["payload"]
        }))

class ScanConsumer(AsyncWebsocketConsumer):
    """
    Handles per-scan real-time terminal output and status.
    Path: ws/scans/<scan_id>/
    """
    async def connect(self):
        self.user = self.scope["user"]
        self.scan_id = self.scope["url_route"]["kwargs"]["scan_id"]

        if self.user.is_anonymous:
            await self.accept()
            await self.send(text_data="[ERROR] Unauthorized\r\n")
            await self.close()
            return

        # Check if user has access to this scan
        if not await self.has_scan_access():
            await self.accept()
            await self.send(text_data="[ERROR] Forbidden - Access to scan denied\r\n")
            await self.close()
            return

        self.scan_group = f"scan_{self.scan_id}"

        await self.channel_layer.group_add(
            self.scan_group,
            self.channel_name
        )

        await self.accept()

    @database_sync_to_async
    def has_scan_access(self):
        from scans.models import Scan
        from users.models import WorkspaceMember, UserRole
        try:
            # Admins and Superadmins have access to everything
            if self.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
                return True
                
            # Check if scan exists
            scan = Scan.objects.get(pk=self.scan_id)
            workspace = scan.target.workspace
            
            # Check if user is the owner of the target
            if scan.target.owner == self.user:
                return True
                
            # Check if user is a member of the workspace
            return WorkspaceMember.objects.filter(workspace=workspace, user=self.user).exists()
        except Exception:
            return False

    async def disconnect(self, close_code):
        if hasattr(self, "scan_group"):
            await self.channel_layer.group_discard(
                self.scan_group,
                self.channel_name
            )

    async def scan_terminal_line(self, event):
        """Handler for 'scan_terminal_line' events."""
        # Simple text for the terminal
        await self.send(text_data=event["data"])
