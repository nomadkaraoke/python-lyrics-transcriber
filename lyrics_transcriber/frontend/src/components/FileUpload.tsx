import { ChangeEvent, DragEvent, useState } from 'react'
import { Paper, Typography } from '@mui/material'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import { CorrectionData } from '../types'

interface FileUploadProps {
    onUpload: (data: CorrectionData) => void
}

export default function FileUpload({ onUpload }: FileUploadProps) {
    const [isDragging, setIsDragging] = useState(false)

    const handleDragOver = (e: DragEvent) => {
        e.preventDefault()
        setIsDragging(true)
    }

    const handleDragLeave = () => {
        setIsDragging(false)
    }

    const handleDrop = async (e: DragEvent) => {
        e.preventDefault()
        setIsDragging(false)
        const file = e.dataTransfer.files[0]
        await processFile(file)
    }

    const handleFileInput = async (e: ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.length) {
            await processFile(e.target.files[0])
        }
    }

    const processFile = async (file: File) => {
        try {
            const text = await file.text()
            const data = JSON.parse(text)
            onUpload(data)
        } catch (error) {
            console.error('Error processing file:', error)
            // TODO: Add error handling UI
        }
    }

    return (
        <Paper
            sx={{
                p: 4,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                backgroundColor: isDragging ? 'action.hover' : 'background.paper',
                cursor: 'pointer',
            }}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => document.getElementById('file-input')?.click()}
        >
            <input
                type="file"
                id="file-input"
                style={{ display: 'none' }}
                accept="application/json"
                onChange={handleFileInput}
            />
            <CloudUploadIcon sx={{ fontSize: 48, mb: 2 }} />
            <Typography variant="h6" gutterBottom>
                Upload Lyrics Correction Review JSON
            </Typography>
            <Typography variant="body2" color="text.secondary">
                Drag and drop a file here, or click to select
            </Typography>
        </Paper>
    )
} 