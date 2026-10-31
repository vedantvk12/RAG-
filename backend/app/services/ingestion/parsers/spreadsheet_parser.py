import pandas as pd
from app.services.ingestion.parsers import DocumentParser, ParsedDocument
from app.services.ingestion.chunking import ExtractedChunk, DocumentChunkMetadata

class SpreadsheetParser(DocumentParser):
    def parse(self, file_path: str, original_filename: str) -> ParsedDocument:
        chunks = []
        if original_filename.lower().endswith(".csv"):
            df = pd.read_csv(file_path)
            self._process_dataframe(df, "Sheet1", chunks)
        elif original_filename.lower().endswith(".xlsx"):
            # read all sheets
            excel_data = pd.read_excel(file_path, sheet_name=None)
            for sheet_name, df in excel_data.items():
                self._process_dataframe(df, sheet_name, chunks)
                
        return ParsedDocument(chunks=chunks)

    def _process_dataframe(self, df: pd.DataFrame, sheet_name: str, chunks: list):
        if df.empty:
            return
            
        # We chunk large dataframes by converting them to CSV representations, maybe 50 rows per chunk
        chunk_size = 50
        for i in range(0, len(df), chunk_size):
            chunk_df = df.iloc[i:i+chunk_size]
            text = chunk_df.to_csv(index=False)
            metadata = DocumentChunkMetadata(
                page_number=None,
                section=sheet_name,
                source_type="table"
            )
            chunks.append(ExtractedChunk(text=text, metadata=metadata))
