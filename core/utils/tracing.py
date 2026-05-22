import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

def init_tracing(service_name: str, app=None):
    """
    👁️ [ZENITH-TRACE-INIT]: Khởi tạo cảm biến X-Ray cho dịch vụ.
    Kết nối nơ-ron trực tiếp tới Jaeger Collector.
    """
    try:
        # 🏛️ [RESOURCE-TAGGING]: Định danh dịch vụ trong hệ sinh thái JKAI
        resource = Resource.create({"service.name": service_name})
        
        # 🛰️ [UPLINK-CONFIG]: Gửi dữ liệu tới Jaeger thông qua OTLP gRPC
        # 'jaeger' là tên container trong mạng nội bộ docker-compose
        otlp_exporter = OTLPSpanExporter(endpoint="http://jaeger:4317", insecure=True)
        
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(span_processor)
        
        trace.set_tracer_provider(tracer_provider)
        
        # 🚀 [FASTAPI-AUTO-INSTRUMENT]: Tự động soi chiếu các API
        if app:
            FastAPIInstrumentor.instrument_app(app)
            
        print(f"📡 [JKAI-XRAY] Tracing initialized for {service_name}")
        return trace.get_tracer(service_name)
    except Exception as e:
        print(f"⚠️ [JKAI-XRAY] Tracing initialization failed: {e}")
        return trace.get_tracer(service_name)
