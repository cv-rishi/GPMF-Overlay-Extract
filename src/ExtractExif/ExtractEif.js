const gpmfExtract = require('gpmf-extract');
const goproTelemetry = require('gopro-telemetry');
const fs = require('fs');
const path = require('path');

if (process.argv.length < 3) {
    console.error("Usage: node ExtractEif.js <inputFile>");
    process.exit(1);
}

const inputFile = process.argv[2];

try {
    const fileStream = fs.createReadStream(inputFile);
    
    const chunks = [];
    fileStream.on('data', chunk => {
        chunks.push(chunk);
    });

    fileStream.on('end', () => {
        const fileBuffer = Buffer.concat(chunks);

        gpmfExtract(fileBuffer)
            .then(extracted => {
                goproTelemetry(extracted, {}, telemetry => {
                    console.log(JSON.stringify(telemetry));
                });
            })
            .catch(error => {
                console.error("Error extracting telemetry:", error);
                process.exit(1);
            });
    });

    fileStream.on('error', error => {
        console.error("Error reading input file:", error);
        process.exit(1);
    });
} catch (error) {
    console.error("Unexpected error:", error);
    process.exit(1);
}

