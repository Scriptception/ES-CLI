"""Elasticsearch client wrapper with KQL and ESQL support."""
from typing import Dict, Any, List, Optional
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError, ConnectionError
import requests
from requests.auth import HTTPBasicAuth
import urllib3
import warnings

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='.*verify_certs=False.*')
warnings.filterwarnings('ignore', message='.*TLS.*insecure.*')


class ESClient:
    """Wrapper around Elasticsearch client with KQL and ESQL query support."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Elasticsearch client.
        
        Args:
            config: Elasticsearch configuration dictionary.
        """
        # Store original config for direct HTTP requests
        self._original_config = config.copy()
        
        # Validate config
        if not isinstance(config, dict):
            raise ValueError(f"Config must be a dictionary, got {type(config)}")
        
        # Clean config for Elasticsearch client
        clean_config = {}
        ignored_keys = {'use_ssl', 'Optional', 'optional'}
        
        valid_keys = {
            'hosts', 'host', 'cloud_id', 'api_key', 'basic_auth', 'bearer_auth',
            'opaque_id', 'headers', 'connections_per_node', 'http_compress',
            'verify_certs', 'ca_certs', 'client_cert', 'client_key', 'ssl_assert_hostname',
            'ssl_assert_fingerprint', 'ssl_version', 'ssl_show_warn',
            'max_retries', 'retry_on_status', 'retry_on_timeout',
            'sniff_on_start', 'sniff_on_connection_fail', 'sniffer_timeout', 'sniff_timeout',
            'min_delay_between_sniffing', 'timeout', 'max_timeout'
        }
        
        for k, v in config.items():
            if v is None or not isinstance(k, str) or k in ignored_keys:
                continue
            if k in valid_keys or k.startswith('http_') or k.startswith('request_'):
                # Convert basic_auth from dict to tuple format expected by SDK
                if k == 'basic_auth' and isinstance(v, dict):
                    username = v.get('username', '')
                    password = v.get('password', '')
                    clean_config[k] = (username, password)
                else:
                    clean_config[k] = v
        
        # Handle use_ssl
        if config.get('use_ssl', False) and 'hosts' in clean_config:
            hosts = clean_config['hosts']
            if isinstance(hosts, list):
                clean_config['hosts'] = [
                    host if host.startswith(('http://', 'https://')) else f'https://{host}'
                    for host in hosts
                ]
            elif isinstance(hosts, str) and not hosts.startswith(('http://', 'https://')):
                clean_config['hosts'] = f'https://{hosts}'
        
        if 'hosts' not in clean_config and 'host' not in clean_config:
            clean_config.setdefault('hosts', ['http://localhost:9200'])
        
        try:
            self.client = Elasticsearch(**clean_config)
        except TypeError as e:
            raise ValueError(
                f"Invalid Elasticsearch configuration. Error: {e}\n"
                f"Config keys provided: {list(config.keys())}"
            ) from e
        
        # Skip connection test if there are SDK decode issues - we'll test on first query instead
        try:
            self._test_connection()
        except Exception as e:
            error_str = str(e)
            if 'decode' in error_str.lower() or "'dict' object has no attribute 'decode'" in error_str:
                # SDK has an internal issue, but client might still work
                # Skip the test and continue - we'll catch errors on actual queries
                import warnings
                warnings.warn(
                    f"Connection test skipped due to SDK issue: {e}. "
                    "The client will still work for queries.",
                    UserWarning
                )
            else:
                raise
    
    def _test_connection(self):
        """Test connection to Elasticsearch."""
        try:
            result = self.client.ping()
            if not result:
                raise ConnectionError("Cannot connect to Elasticsearch cluster")
        except AttributeError as e:
            # Catch decode errors that might happen in SDK
            if 'decode' in str(e):
                # SDK internal error, but connection might still work
                # Just warn and continue
                import warnings
                warnings.warn(f"Connection test had an issue: {e}, but continuing...")
                return
            raise ConnectionError(f"Failed to connect to Elasticsearch: {e}")
        except Exception as e:
            # Check if it's a decode error
            error_str = str(e)
            if 'decode' in error_str.lower() or "'dict' object has no attribute 'decode'" in error_str:
                # SDK internal error, but connection might still work
                import warnings
                warnings.warn(f"Connection test had an issue: {e}, but continuing...")
                return
            raise ConnectionError(f"Failed to connect to Elasticsearch: {e}")
    
    def _get_base_url(self) -> str:
        """Get base URL from config."""
        hosts = self._original_config.get('hosts', ['http://localhost:9200'])
        if isinstance(hosts, list) and len(hosts) > 0:
            return hosts[0].rstrip('/')
        elif isinstance(hosts, str):
            return hosts.rstrip('/')
        return 'http://localhost:9200'
    
    def _get_auth(self):
        """Get authentication from config."""
        if 'basic_auth' in self._original_config:
            basic_auth = self._original_config['basic_auth']
            if isinstance(basic_auth, dict):
                username = basic_auth.get('username', '')
                password = basic_auth.get('password', '')
                if username and password:
                    return HTTPBasicAuth(username, password)
        return None
    
    def _get_verify(self):
        """Get SSL verification setting from config."""
        verify = self._original_config.get('verify_certs', True)
        if verify is False:
            return False
        elif isinstance(verify, str):
            return verify  # Path to CA cert
        return True
    
    def search_kql(
        self,
        query: str,
        index: str = "*",
        size: int = 100,
        from_: int = 0,
        sort: Optional[List[Dict[str, Any]]] = None,
        time_range: Optional[tuple] = None,
        time_field: str = "@timestamp"
    ) -> Dict[str, Any]:
        """Execute a KQL (Kibana Query Language) query.
        
        Args:
            query: KQL query string (e.g., "status:200 AND response_time:>100")
            index: Index pattern to search (default: "*")
            size: Number of results to return
            from_: Starting offset for pagination
            sort: List of sort specifications
            time_range: Optional tuple of (start_time, end_time) datetime objects
            time_field: Field name for time filtering (default: "@timestamp")
            
        Returns:
            Elasticsearch search response
        """
        try:
            # Build query
            query_clauses = []
            
            # Add time range filter if provided
            if time_range:
                start_time, end_time = time_range
                time_filter = {
                    "range": {
                        time_field: {
                            "gte": start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                            "lte": end_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                        }
                    }
                }
                query_clauses.append(time_filter)
            
            # Add user query
            if query.strip():
                query_clauses.append({
                    "query_string": {
                        "query": query
                    }
                })
            
            # Build final query
            if len(query_clauses) == 1:
                final_query = query_clauses[0]
            elif len(query_clauses) > 1:
                final_query = {
                    "bool": {
                        "must": query_clauses
                    }
                }
            else:
                final_query = {"match_all": {}}
            
            search_body = {
                "query": final_query,
                "size": size,
                "from": from_
            }
            
            if sort:
                search_body["sort"] = sort
            else:
                # Default sort by time field descending
                search_body["sort"] = [{time_field: {"order": "desc"}}]
            
            # Use longer timeout for searches (5 minutes)
            response = self.client.search(index=index, body=search_body, timeout='300s', request_timeout=300)
            return response
        except RequestError as e:
            error_info = getattr(e, 'info', {})
            if isinstance(error_info, dict):
                error_msg = error_info.get('error', {}).get('reason', str(e))
            else:
                error_msg = str(e)
            raise ValueError(f"Invalid KQL query: {error_msg}")
        except Exception as e:
            raise RuntimeError(f"Search failed: {e}")
    
    def query_esql(
        self,
        query: str,
        format: str = "json",
        time_range: Optional[tuple] = None,
        time_field: str = "@timestamp"
    ) -> Dict[str, Any]:
        """Execute an ESQL (Elasticsearch Query Language) query.
        
        Args:
            query: ESQL query string (e.g., "FROM logs | WHERE status > 200 | LIMIT 100")
            format: Response format (json, csv, tsv)
            time_range: Optional tuple of (start_time, end_time) datetime objects
            time_field: Field name for time filtering (default: "@timestamp")
            
        Returns:
            ESQL query response
        """
        try:
            # Add time range filter to ESQL query if provided
            if time_range:
                start_time, end_time = time_range
                # Format times for ESQL (ISO 8601 format)
                start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                
                # Check if query already has a WHERE clause
                query_upper = query.upper()
                if 'WHERE' in query_upper:
                    # Add time filter to existing WHERE clause
                    # Find WHERE position and add time condition
                    where_pos = query_upper.find('WHERE')
                    after_where = query[where_pos + 5:].strip()
                    # Add time filter at the beginning of WHERE conditions
                    time_filter = f"{time_field} >= \"{start_str}\" AND {time_field} <= \"{end_str}\" AND "
                    query = query[:where_pos + 5] + " " + time_filter + after_where
                else:
                    # Add WHERE clause with time filter
                    # Find the FROM clause and add WHERE after it
                    from_pos = query_upper.find('FROM')
                    if from_pos != -1:
                        # Find where FROM clause ends (usually at | or end)
                        pipe_pos = query.find('|', from_pos)
                        if pipe_pos != -1:
                            # Insert WHERE clause before the pipe
                            query = query[:pipe_pos].strip() + f" | WHERE {time_field} >= \"{start_str}\" AND {time_field} <= \"{end_str}\" | " + query[pipe_pos + 1:].strip()
                        else:
                            # No pipe found, add WHERE at the end
                            query = query.strip() + f" | WHERE {time_field} >= \"{start_str}\" AND {time_field} <= \"{end_str}\""
            
            # Build URL
            base_url = self._get_base_url()
            url = f"{base_url}/_query"
            
            # Prepare request
            params = {"format": format} if format else {}
            payload = {"query": query}
            
            # Get auth and SSL settings
            auth = self._get_auth()
            verify = self._get_verify()
            
            # Make HTTP request directly using requests with extended timeout (10 minutes)
            # ESQL queries can take longer, especially on large datasets
            response = requests.post(
                url,
                json=payload,
                auth=auth,
                params=params,
                timeout=600,  # 10 minutes for ESQL queries
                verify=verify
            )
            
            # Raise for HTTP errors
            response.raise_for_status()
            
            # Return JSON response - requests handles this correctly
            return response.json()
                
        except requests.exceptions.HTTPError as e:
            # Handle HTTP errors
            if e.response is not None:
                status_code = e.response.status_code
                if status_code == 504:
                    # Gateway timeout - query took too long
                    raise RuntimeError(
                        "ESQL query timed out (504 Gateway Timeout). "
                        "The query is taking too long to execute. "
                        "Try: 1) Reducing the time range, 2) Adding a LIMIT clause, "
                        "3) Making the query more specific, or 4) Using KQL instead."
                    )
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', {}).get('reason', str(e))
                except:
                    error_msg = f"HTTP {status_code}: {str(e)}"
            else:
                error_msg = str(e)
            raise ValueError(f"Invalid ESQL query: {error_msg}")
        except requests.exceptions.Timeout as e:
            raise RuntimeError(
                "ESQL query timed out. The query took longer than 10 minutes to execute. "
                "Try: 1) Reducing the time range, 2) Adding a LIMIT clause, "
                "3) Making the query more specific, or 4) Using KQL instead."
            )
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"ESQL query failed: {e}")
        except Exception as e:
            raise RuntimeError(f"ESQL query failed: {e}")
    
    def get_indices(self, pattern: str = "*") -> List[str]:
        """Get list of indices matching pattern.
        
        Args:
            pattern: Index pattern (default: "*")
            
        Returns:
            List of index names
        """
        try:
            indices = self.client.indices.get_alias(index=pattern)
            return list(indices.keys())
        except Exception:
            return []
    
    def get_index_info(self, index: str) -> Dict[str, Any]:
        """Get information about an index.
        
        Args:
            index: Index name
            
        Returns:
            Index information including mappings
        """
        try:
            return self.client.indices.get(index=index)
        except Exception as e:
            raise ValueError(f"Failed to get index info: {e}")
