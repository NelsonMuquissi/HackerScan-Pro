import asyncio
import logging
from typing import AsyncGenerator, List
from .base import BaseScanStrategy, FindingData, register
from scans.models import Severity
from ..utils import make_evidence_request_async

try:
    import motor.motor_asyncio
    HAS_MOTOR = True
except ImportError:
    HAS_MOTOR = False

logger = logging.getLogger(__name__)

@register
class DatabaseAuditStrategy(BaseScanStrategy):
    slug = "db_audit"
    name = "Database & Cache Exposure Audit"
    description = "Checks for unauthenticated access to NoSQL databases and caching systems (Redis, MongoDB, Elasticsearch, Memcached)."

    async def run_async(self, target, scan) -> AsyncGenerator[FindingData, None]:
        db_ports = {
            6379: "Redis",
            27017: "MongoDB",
            9200: "Elasticsearch",
            11211: "Memcached",
            5984: "CouchDB"
        }
        
        self.log(scan, f"Auditing {len(db_ports)} database/cache services for unauthenticated exposure...")
        
        # Initial port check
        opened = []
        for port in db_ports.keys():
            try:
                conn = asyncio.open_connection(target.host, port)
                _, writer = await asyncio.wait_for(conn, timeout=1.0)
                writer.close()
                await writer.wait_closed()
                opened.append(port)
            except Exception:
                continue

        for port in opened:
            service = db_ports[port]
            
            if service == "Redis":
                yield await self._audit_redis(target.host, port)
            elif service == "MongoDB":
                yield await self._audit_mongodb(target.host, port)
            elif service == "Elasticsearch":
                async for f in self._audit_elasticsearch(target.host, port):
                    yield f
            elif service == "Memcached":
                yield await self._audit_memcached(target.host, port)
            elif service == "CouchDB":
                yield await self._audit_couchdb(target.host, port)

    async def _audit_redis(self, host: str, port: int) -> FindingData:
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=3.0)
            writer.write(b"INFO\r\n")
            await writer.drain()
            response = await asyncio.wait_for(reader.read(4096), timeout=3.0)
            
            # Try to get some keys as additional proof
            writer.write(b"SCAN 0 COUNT 5\r\n")
            await writer.drain()
            keys_resp = await asyncio.wait_for(reader.read(1024), timeout=2.0)
            
            writer.close()
            await writer.wait_closed()
            
            content = response.decode(errors='ignore')
            keys_content = keys_resp.decode(errors='ignore')
            
            if "redis_version" in content:
                # Extract some key info
                version = "Unknown"
                os = "Unknown"
                clients = "0"
                for line in content.splitlines():
                    if line.startswith("redis_version:"): version = line.split(":")[1].strip()
                    if line.startswith("os:"): os = line.split(":")[1].strip()
                    if line.startswith("connected_clients:"): clients = line.split(":")[1].strip()
                
                proof = f"Version: {version}, OS: {os}, Connected Clients: {clients}"
                if "*" in keys_content: # Basic check for redis RESP array
                    proof += f"\nKeys Sample: Found active keys in DB."

                return FindingData(
                    severity=Severity.CRITICAL,
                    title="Unauthenticated Redis Instance Exposed",
                    description=f"Redis instance on {host}:{port} allows unauthenticated access.\n\n**REAL DATA PROOF**:\n{proof}",
                    evidence={"version": version, "os": os, "raw_info": content[:1000]},
                    remediation="Enable 'requirepass' in redis.conf and bind to localhost or use a VPC/Firewall.",
                    plugin_slug=self.slug,
                    poc=f"redis-cli -h {host} INFO",
                    is_verified=True
                )
        except Exception:
            pass
            
        return FindingData(
            severity=Severity.MEDIUM,
            title="Redis Port Exposed",
            description=f"Redis port {port} is open on {host}, but unauthenticated INFO command failed.",
            evidence={"port": port},
            plugin_slug=self.slug
        )

    async def _audit_memcached(self, host: str, port: int) -> FindingData:
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=3.0)
            writer.write(b"stats\r\n")
            await writer.drain()
            response = await asyncio.wait_for(reader.read(1024), timeout=3.0)
            writer.close()
            await writer.wait_closed()
            
            content = response.decode(errors='ignore')
            if "STAT pid" in content:
                version = "Unknown"
                uptime = "0"
                for line in content.splitlines():
                    if line.startswith("STAT version"): version = line.split()[2].strip()
                    if line.startswith("STAT uptime"): uptime = line.split()[2].strip()
                
                return FindingData(
                    severity=Severity.HIGH,
                    title="Unauthenticated Memcached Instance Exposed",
                    description=f"Memcached on {host}:{port} is open and allows unauthenticated stats retrieval.\n\n**REAL DATA PROOF**: Version: {version}, Uptime: {uptime}s",
                    evidence={"version": version, "raw_stats": content},
                    remediation="Bind memcached to localhost or use a firewall to restrict access.",
                    plugin_slug=self.slug,
                    poc=f"echo 'stats' | nc {host} {port}",
                    is_verified=True
                )
        except Exception:
            pass
        return FindingData(severity=Severity.LOW, title="Memcached Port Exposed", evidence={"port": port}, plugin_slug=self.slug)

    async def _audit_elasticsearch(self, host: str, port: int) -> AsyncGenerator[FindingData, None]:
        url = f"http://{host}:{port}"
        try:
            resp, req, res, poc = await make_evidence_request_async(url, timeout=5)
            if resp and resp.status_code == 200 and "cluster_name" in resp.text:
                data = resp.json()
                version = data.get("version", {}).get("number", "Unknown")
                cluster = data.get("cluster_name", "Unknown")
                
                # Try to list indices
                indices_url = f"{url}/_cat/indices?v"
                indices_resp, _, _, _ = await make_evidence_request_async(indices_url, timeout=5)
                indices_snippet = indices_resp.text[:500] if (indices_resp and indices_resp.status_code == 200) else "Access Denied"
                
                yield FindingData(
                    severity=Severity.CRITICAL,
                    title="Unauthenticated Elasticsearch Exposed",
                    description=f"Elasticsearch cluster '{cluster}' is exposed at {url}.\n\n**REAL DATA PROOF**:\nVersion: {version}\nIndices Snippet:\n```\n{indices_snippet}\n```",
                    evidence={"version": version, "cluster": cluster, "indices": indices_snippet},
                    remediation="Enable X-Pack security, set a password, or restrict access via Firewall/VPC.",
                    plugin_slug=self.slug,
                    request=req,
                    response=res,
                    poc=f"curl {url}/_cat/indices?v",
                    is_verified=True
                )
                return
        except Exception:
            pass
        yield FindingData(severity=Severity.LOW, title="Elasticsearch Port Exposed", evidence={"port": port}, plugin_slug=self.slug)

    async def _audit_mongodb(self, host: str, port: int) -> FindingData:
        if not HAS_MOTOR:
            return FindingData(severity=Severity.INFO, title="MongoDB Port Open (Driver Missing)", evidence={"port": port}, plugin_slug=self.slug)
            
        try:
            client = motor.motor_asyncio.AsyncIOMotorClient(f"mongodb://{host}:{port}", serverSelectionTimeoutMS=2000)
            
            # Get server build info for version
            build_info = await client.admin.command('buildInfo')
            version = build_info.get('version', 'Unknown')
            
            # List databases as ultimate proof
            dbs = await client.list_database_names()
            dbs_str = ", ".join(dbs)
            
            return FindingData(
                severity=Severity.CRITICAL,
                title="Unauthenticated MongoDB Instance Exposed",
                description=f"MongoDB on {host}:{port} allows unauthenticated access.\n\n**REAL DATA PROOF**: Version: {version}, Databases Found: {dbs_str}",
                evidence={"version": version, "databases": dbs, "build_info": build_info},
                remediation="Enable auth in mongod.conf and bind to trusted IPs.",
                plugin_slug=self.slug,
                poc=f"mongo --host {host} --port {port} --eval 'db.adminCommand(\"listDatabases\")'",
                is_verified=True
            )
        except Exception:
            pass
        return FindingData(severity=Severity.MEDIUM, title="MongoDB Port Exposed", evidence={"port": port}, plugin_slug=self.slug)

    async def _audit_couchdb(self, host: str, port: int) -> FindingData:
        url = f"http://{host}:{port}/"
        try:
            resp, req, res, poc = await make_evidence_request_async(url, timeout=5)
            if resp and resp.status_code == 200 and "couchdb" in resp.text:
                data = resp.json()
                version = data.get("version", "Unknown")
                
                # Try to list databases
                all_dbs_url = f"{url}_all_dbs"
                dbs_resp, _, _, _ = await make_evidence_request_async(all_dbs_url, timeout=5)
                dbs_proof = dbs_resp.text if (dbs_resp and dbs_resp.status_code == 200) else "Listing Denied"

                return FindingData(
                    severity=Severity.HIGH,
                    title="Unauthenticated CouchDB Exposed",
                    description=f"CouchDB instance is exposed at {url}.\n\n**REAL DATA PROOF**: Version: {version}, Databases: {dbs_proof}",
                    evidence=data,
                    remediation="Configure admin users and enable authentication.",
                    plugin_slug=self.slug,
                    request=req,
                    response=res,
                    poc=poc,
                    is_verified=True
                )
        except Exception:
            pass
        return FindingData(severity=Severity.LOW, title="CouchDB Port Exposed", evidence={"port": port}, plugin_slug=self.slug)

    async def verify_async(self, finding) -> bool:
        """
        Re-probes the target database to confirm exposure and capture fresh evidence.
        """
        from asgiref.sync import sync_to_async
        
        try:
            scan = await sync_to_async(lambda: finding.scan)()
            target = await sync_to_async(lambda: scan.target)()
            host = target.host
            
            # Identify port from evidence or title defaults
            port = finding.evidence.get("port")
            if not port:
                if "Redis" in finding.title: port = 6379
                elif "MongoDB" in finding.title: port = 27017
                elif "Elasticsearch" in finding.title: port = 9200
                elif "Memcached" in finding.title: port = 11211
                elif "CouchDB" in finding.title: port = 5984
            
            if not port:
                return False

            self.log(scan, f"Verifying database exposure finding: {finding.title} on {host}:{port}")
            
            res = None
            if "Redis" in finding.title:
                res = await self._audit_redis(host, port)
            elif "MongoDB" in finding.title:
                res = await self._audit_mongodb(host, port)
            elif "Elasticsearch" in finding.title:
                async for f in self._audit_elasticsearch(host, port):
                    if f.is_verified:
                        res = f
                        break
            elif "Memcached" in finding.title:
                res = await self._audit_memcached(host, port)
            elif "CouchDB" in finding.title:
                res = await self._audit_couchdb(host, port)

            if res and res.is_verified:
                finding.is_verified = True
                finding.evidence = res.evidence
                finding.description = res.description
                finding.poc = res.poc
                if res.request: finding.request = res.request
                if res.response: finding.response = res.response
                
                await sync_to_async(finding.save)()
                self.log(scan, f"Successfully verified: {finding.title}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error verifying database finding {finding.id}: {e}")
            return False

